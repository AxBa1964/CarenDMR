"""Hart verriegelter Sprachtest zum BrandMeister-Parrot (Privatruf 9990/TS2)."""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass

from carendmr.audio import BufferedPcmOutput
from carendmr.encoder import AmbeEncoder
from carendmr.network import NetworkReceiveTimeout
from carendmr.vocoder import NativeMbeReceiveVocoder, extract_ambe_codewords
from carendmr.vocoder.playout import DmrJitterBuffer

from .client import BrandMeisterClient
from .config import BrandMeisterConfig
from .dmrd import DmrdCallType, DmrdDataType, DmrdFrameClass, DmrdPacket, parse_dmrd_packet
from .parrot_profile import (
    PARROT_DESTINATION_ID, PARROT_ECHO_CAP_SECONDS, PARROT_TIMESLOT,
    PARROT_TRANSMIT_CAP_SECONDS, ParrotSafetyError,
)
from .protocol import LoginState
from .silent_call import (
    _MS_AUDIO_SYNC, _add_sync, _bits_to_bytes, _encode_embedded_lc,
    _encode_full_lc_burst, _EMB_CODEWORDS,
)

PACKET_INTERVAL_SECONDS = 0.060
PCM_FRAME_SAMPLES = 160
AMBE_FRAME_BYTES = 9
DEFAULT_PARROT_RECORD_SECONDS = 5.0


@dataclass(frozen=True, slots=True)
class ParrotVoiceResult:
    authenticated: bool
    sent_packets: int
    voice_bursts_sent: int
    transmit_elapsed_seconds: float
    echo_voice_bursts: int
    decoded_codewords: int
    output_samples: int
    decode_errors: int
    echo_received: bool
    timed_out: bool
    closed: bool


class ParrotVoiceError(RuntimeError):
    def __init__(self, message: str, *, sent_packets: int = 0, closed: bool = False):
        super().__init__(message)
        self.sent_packets = sent_packets
        self.closed = closed


def _validate_pcm(pcm_samples: tuple[int, ...]) -> None:
    if not isinstance(pcm_samples, tuple):
        raise TypeError("Parrot-PCM muss als unveränderliches Tupel vorliegen.")
    if not pcm_samples:
        raise ValueError("Die Parrot-Aufnahme ist leer.")
    if len(pcm_samples) > int(8000 * PARROT_TRANSMIT_CAP_SECONDS):
        raise ParrotSafetyError("Die Aufnahme überschreitet die harte 180-Sekunden-Grenze.")
    if any(not isinstance(v, int) or not -32768 <= v <= 32767 for v in pcm_samples):
        raise ValueError("Parrot-PCM enthält ungültige 16-Bit-Samples.")


def _pack_ambe(codewords: tuple[bytes, bytes, bytes]) -> bytearray:
    if len(codewords) != 3 or any(len(word) != AMBE_FRAME_BYTES for word in codewords):
        raise ValueError("Ein DMR-Sprachburst benötigt genau drei 9-Byte-AMBE-Rahmen.")
    packed = b"".join(codewords)
    burst = bytearray(33)
    burst[:13] = packed[:13]
    burst[13] = packed[13] & 0xF0
    burst[19] = packed[13] & 0x0F
    burst[20:33] = packed[14:27]
    return burst


def _apply_embedded_lc(burst: bytearray, number: int, embedded: tuple[bool, ...]) -> None:
    lcss = 0
    if 1 <= number < 5:
        fragment = embedded[(number - 1) * 32:number * 32]
        packed = _bits_to_bytes((False,) * 4 + fragment + (False,) * 4)
        burst[14] = (burst[14] & 0xF0) | (packed[0] & 0x0F)
        burst[15:18] = packed[1:4]
        burst[18] = (burst[18] & 0x0F) | (packed[4] & 0xF0)
        lcss = 1 if number == 1 else 2 if number == 4 else 3
    else:
        burst[14] &= 0xF0
        burst[15:18] = b"\x00\x00\x00"
        burst[18] &= 0x0F
    codeword = _EMB_CODEWORDS[lcss]
    emb0, emb1 = codeword >> 8, codeword & 0xFF
    burst[13] = (burst[13] & 0xF0) | ((emb0 >> 4) & 0x0F)
    burst[14] = (burst[14] & 0x0F) | ((emb0 << 4) & 0xF0)
    burst[18] = (burst[18] & 0xF0) | ((emb1 >> 4) & 0x0F)
    burst[19] = (burst[19] & 0x0F) | ((emb1 << 4) & 0xF0)


def build_locked_parrot_voice_packets(
    *, source_id: int, repeater_id: int, stream_id: int, first_sequence: int,
    pcm_samples: tuple[int, ...], encoder: AmbeEncoder,
) -> tuple[DmrdPacket, ...]:
    """Erzeugt ausschließlich Privatruf 9990/TS2 aus höchstens hundertachtzig Sekunden PCM."""
    _validate_pcm(pcm_samples)
    if not 1 <= source_id <= 0xFFFFFF:
        raise ValueError("Die DMR-ID passt nicht in das Quellfeld.")
    if not 1 <= stream_id <= 0xFFFFFFFF:
        raise ValueError("Die Stream-ID ist ungültig.")
    if not 0 <= first_sequence <= 0xFF:
        raise ValueError("Die Sequenznummer ist ungültig.")

    frames = []
    for offset in range(0, len(pcm_samples), PCM_FRAME_SAMPLES):
        frame = pcm_samples[offset:offset + PCM_FRAME_SAMPLES]
        if len(frame) < PCM_FRAME_SAMPLES:
            frame = frame + (0,) * (PCM_FRAME_SAMPLES - len(frame))
        encoded = encoder.encode_2450x1150(frame)
        if len(encoded) != AMBE_FRAME_BYTES:
            raise ParrotSafetyError("Der Encoder lieferte keinen 9-Byte-AMBE-Rahmen.")
        frames.append(encoded)
    while len(frames) % 3:
        frames.append(encoder.encode_2450x1150((0,) * PCM_FRAME_SAMPLES))

    link_control = (
        bytes((0x03, 0, 0)) + PARROT_DESTINATION_ID.to_bytes(3, "big")
        + source_id.to_bytes(3, "big")
    )
    embedded = _encode_embedded_lc(link_control)
    packets: list[DmrdPacket] = []
    sequence = first_sequence

    def add(payload: bytes, frame_class: DmrdFrameClass, *, voice_no=None, data_type=None):
        nonlocal sequence
        packet = DmrdPacket(
            sequence=sequence, source_id=source_id, destination_id=PARROT_DESTINATION_ID,
            repeater_id=repeater_id, timeslot=PARROT_TIMESLOT,
            call_type=DmrdCallType.PRIVATE, frame_class=frame_class,
            stream_id=stream_id, payload=payload, voice_frame_number=voice_no,
            data_type=data_type,
        )
        raw = packet.to_bytes()
        if packet.destination_id != 9990 or packet.timeslot != 2 or not raw[15] & 0x40:
            raise ParrotSafetyError("Die private Parrot-Verriegelung ist verletzt.")
        packets.append(packet)
        sequence = (sequence + 1) & 0xFF

    add(_encode_full_lc_burst(link_control, 0x01), DmrdFrameClass.DATA_SYNC,
        data_type=DmrdDataType.VOICE_LC_HEADER.value)
    for burst_index in range(0, len(frames), 3):
        number = (burst_index // 3) % 6
        burst = _pack_ambe(tuple(frames[burst_index:burst_index + 3]))
        if number == 0:
            _add_sync(burst, _MS_AUDIO_SYNC)
            add(bytes(burst), DmrdFrameClass.VOICE_SYNC)
        else:
            _apply_embedded_lc(burst, number, embedded)
            add(bytes(burst), DmrdFrameClass.VOICE, voice_no=number)
    add(_encode_full_lc_burst(link_control, 0x02), DmrdFrameClass.DATA_SYNC,
        data_type=DmrdDataType.TERMINATOR_WITH_LC.value)
    return tuple(packets)


def execute_locked_parrot_voice_once(
    config: BrandMeisterConfig, *, pcm_samples: tuple[int, ...], encoder: AmbeEncoder,
    client_factory=BrandMeisterClient, output_factory=BufferedPcmOutput,
    decoder_factory=NativeMbeReceiveVocoder,
    sequence_factory=lambda: secrets.randbelow(256),
    stream_factory=lambda: secrets.randbelow(0xFFFFFFFF) + 1,
    monotonic=time.monotonic, sleep=time.sleep,
) -> ParrotVoiceResult:
    packets = build_locked_parrot_voice_packets(
        source_id=config.dmr_id, repeater_id=config.dmr_id,
        stream_id=stream_factory(), first_sequence=sequence_factory(),
        pcm_samples=pcm_samples, encoder=encoder,
    )
    client = client_factory(config)
    output = output_factory(sample_rate=8000)
    decoder = None
    jitter = DmrJitterBuffer()
    authenticated = echo_received = timed_out = closed = False
    sent = voice_sent = echo_voice = decoded_words = output_samples = decode_errors = 0
    tx_elapsed = 0.0
    error = None
    try:
        output.start()
        decoder = decoder_factory()
        client.login()
        authenticated = client.state is LoginState.CONNECTED
        if not authenticated or client.transport is None:
            raise ParrotSafetyError("Die BrandMeister-Anmeldung ist nicht eindeutig verbunden.")
        tx_start = monotonic()
        for index, packet in enumerate(packets):
            elapsed = monotonic() - tx_start
            if elapsed >= PARROT_TRANSMIT_CAP_SECONDS:
                raise ParrotSafetyError("Die harte Sendezeitgrenze wurde erreicht.")
            raw = packet.to_bytes()
            if packet.destination_id != 9990 or packet.timeslot != 2 or packet.call_type is not DmrdCallType.PRIVATE or not raw[15] & 0x40:
                raise ParrotSafetyError("Ein Paket verletzt die private Parrot-Verriegelung.")
            if client.transport.send(raw) != len(raw):
                raise ParrotSafetyError("Ein DMRD-Paket wurde nicht vollständig gesendet.")
            sent += 1
            if packet.frame_class in (DmrdFrameClass.VOICE, DmrdFrameClass.VOICE_SYNC):
                voice_sent += 1
            if index + 1 < len(packets):
                sleep(PACKET_INTERVAL_SECONDS)
        tx_elapsed = monotonic() - tx_start
        if tx_elapsed > PARROT_TRANSMIT_CAP_SECONDS:
            raise ParrotSafetyError("Die Übertragung überschritt 180 Sekunden.")

        echo_start = monotonic()
        while monotonic() - echo_start < PARROT_ECHO_CAP_SECONDS:
            remaining = PARROT_ECHO_CAP_SECONDS - (monotonic() - echo_start)
            if hasattr(client.transport, "set_receive_timeout"):
                client.transport.set_receive_timeout(min(0.5, remaining))
            try:
                datagram = client.transport.receive()
            except NetworkReceiveTimeout:
                continue
            if not datagram.startswith(b"DMRD"):
                continue
            try:
                packet = parse_dmrd_packet(datagram)
            except (TypeError, ValueError):
                continue
            if packet.call_type is not DmrdCallType.PRIVATE or packet.timeslot != 2 or 9990 not in (packet.source_id, packet.destination_id):
                continue
            if packet.is_voice_lc_header:
                decoder.close(); decoder = decoder_factory(); jitter.reset(first_voice_sequence=(packet.sequence + 1) & 0xFF)
                continue
            if packet.is_terminator_with_lc:
                batch = jitter.flush()
                for frame in batch.frames:
                    output.write(frame); output_samples += len(frame)
                echo_received = echo_voice > 0
                break
            if packet.frame_class not in (DmrdFrameClass.VOICE, DmrdFrameClass.VOICE_SYNC):
                continue
            echo_voice += 1
            decoded = []
            try:
                for word in extract_ambe_codewords(packet):
                    frame = decoder.decode(word); decoded.extend(frame.samples); decoded_words += 1
            except Exception:
                decode_errors += 1; continue
            batch = jitter.push(packet.sequence, tuple(decoded))
            for frame in batch.frames:
                output.write(frame); output_samples += len(frame)
        timed_out = not echo_received
        sleep(0.25)
    except Exception as exc:
        error = exc
    finally:
        if decoder is not None:
            decoder.close()
        client.close(); output.close()
        closed = client.transport is None and client.state is LoginState.DISCONNECTED and not output.is_open
    if error is not None:
        raise ParrotVoiceError(
            f"Der private Parrot-Sprachtest wurde sicher abgebrochen: {type(error).__name__}: {error}",
            sent_packets=sent, closed=closed,
        ) from error
    return ParrotVoiceResult(
        authenticated=authenticated, sent_packets=sent, voice_bursts_sent=voice_sent,
        transmit_elapsed_seconds=tx_elapsed, echo_voice_bursts=echo_voice,
        decoded_codewords=decoded_words, output_samples=output_samples,
        decode_errors=decode_errors, echo_received=echo_received, timed_out=timed_out, closed=closed,
    )
