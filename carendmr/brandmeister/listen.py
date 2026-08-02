"""Dynamischer Gruppenruf-Empfang mit Audio-Decodierung und Wiedergabe."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Callable

from carendmr.audio.pcm_output import BufferedPcmOutput
from carendmr.network import NetworkReceiveTimeout
from carendmr.vocoder import NativeMbeReceiveVocoder, extract_ambe_codewords
from carendmr.vocoder.playout import DmrJitterBuffer

from .client import BrandMeisterClient
from .config import BrandMeisterConfig
from .dmrd import DmrdFrameClass, parse_dmrd_packet
from .dynamic_subscription import activate_dynamic_talkgroup, validate_receive_target
from .protocol import LoginState, is_master_pong


MAX_LISTEN_SECONDS = 3600.0
DEFAULT_PROGRESS_INTERVAL_SECONDS = 30.0
DEFAULT_HEARTBEAT_INTERVAL_SECONDS = 5.0
DIAGNOSTIC_SUMMARY_INTERVAL_SECONDS = 5.0


@dataclass(frozen=True, slots=True)
class LiveCallActivity:
    active: bool
    source_id: int
    talkgroup: int
    timeslot: int
    stream_id: int | None


@dataclass(frozen=True, slots=True)
class LiveListenProgress:
    elapsed_seconds: float
    datagrams: int
    target_voice_bursts: int
    decoded_codewords: int
    decode_errors: int
    corrected_errors: int
    concealed_bursts: int
    invalid_dmrd: int


@dataclass(frozen=True, slots=True)
class LiveListenResult:
    authenticated: bool
    audio_started: bool
    synthetic_samples: int
    elapsed_seconds: float
    datagrams: int
    target_voice_bursts: int
    decoded_codewords: int
    decoded_samples: int
    decode_errors: int
    corrected_errors: int
    concealed_bursts: int
    invalid_dmrd: int
    interrupted: bool
    closed: bool


def _synthetic_samples(sample_rate: int = 8000) -> tuple[int, ...]:
    """A quiet 180 ms tone used only to prove the local output path."""

    count = int(sample_rate * 0.18)
    return tuple(
        int(1100 * math.sin(2.0 * math.pi * 440.0 * index / sample_rate))
        for index in range(count)
    )


def listen_receive_only(
    config: BrandMeisterConfig,
    *,
    seconds: float | None,
    target_talkgroup: int = 91,
    target_timeslot: int = 2,
    target_call_type: str = "group",
    progress_callback: Callable[[LiveListenProgress], None] | None = None,
    call_activity_callback: Callable[[LiveCallActivity], None] | None = None,
    progress_interval: float = DEFAULT_PROGRESS_INTERVAL_SECONDS,
    heartbeat_interval: float = DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
    stop_requested: Callable[[], bool] | None = None,
    output_muted: Callable[[], bool] | None = None,
    output_volume: Callable[[], float] | None = None,
    output_agc_enabled: Callable[[], bool] | None = None,
    output_level_callback: Callable[[float], None] | None = None,
    client_factory=BrandMeisterClient,
    output_factory=BufferedPcmOutput,
    decoder_factory=NativeMbeReceiveVocoder,
    monotonic=time.monotonic,
    sleep=time.sleep,
) -> LiveListenResult:
    """Authenticate and receive/decode/play until timeout or Ctrl+C."""

    target_talkgroup, target_timeslot = validate_receive_target(
        target_talkgroup, target_timeslot
    )
    target_call_type = str(target_call_type).strip().lower()
    if target_call_type not in {"group", "private"}:
        raise ValueError("Die Rufart muss group oder private sein.")
    if seconds is not None and (seconds <= 0 or seconds > MAX_LISTEN_SECONDS):
        raise ValueError("Die Empfangsdauer muss zwischen 1 und 3600 Sekunden liegen.")
    if progress_interval <= 0:
        raise ValueError("Das Diagnoseintervall muss größer als null sein.")
    if heartbeat_interval <= 0:
        raise ValueError("Das Heartbeat-Intervall muss größer als null sein.")

    client = client_factory(config)
    output = output_factory(
        sample_rate=8000, muted=output_muted, volume=output_volume,
        agc_enabled=output_agc_enabled, level_callback=output_level_callback,
    )
    decoder = None
    jitter = DmrJitterBuffer()
    authenticated = audio_started = closed = interrupted = False
    synthetic_count = datagrams = voice = codewords = samples = 0
    decode_errors = corrected = concealed = invalid = 0
    started_at = monotonic()
    next_progress = started_at + progress_interval
    next_heartbeat = started_at + heartbeat_interval
    next_diagnostic_summary = started_at + DIAGNOSTIC_SUMMARY_INTERVAL_SECONDS
    rejected_tg = rejected_ts = rejected_call_type = rejected_frame = 0
    headers = terminators = audio_writes = audio_samples = non_dmrd = pongs = 0

    try:
        output.start()
        audio_started = True
        print("[DIAG][AUDIO] Ausgabestream geöffnet: 8000 Hz, mono, int16", flush=True)
        synthetic = _synthetic_samples()
        if output_muted is None or not output_muted():
            output.write(synthetic)
        synthetic_count = len(synthetic)
        sleep(0.25)

        decoder = decoder_factory()
        print("[DIAG][DECODER] Nativer MBE-Decoder geöffnet", flush=True)
        print(f"[DIAG][NETZ] Verbinde mit {config.host}:{config.port}", flush=True)
        client.login()
        authenticated = client.state is LoginState.CONNECTED
        if not authenticated or client.transport is None:
            raise RuntimeError("Die Empfangsverbindung ist nicht eindeutig aktiv.")
        print("[DIAG][NETZ] BrandMeister-Anmeldung erfolgreich", flush=True)
        print(
            f"[DIAG][ZIEL] Aktiviere TG {target_talkgroup} auf TS{target_timeslot}",
            flush=True,
        )

        activate_dynamic_talkgroup(
            client.transport,
            dmr_id=config.dmr_id,
            talkgroup=target_talkgroup,
            timeslot=target_timeslot,
            call_type=target_call_type,
        )
        print("[DIAG][ZIEL] Aktivierungsruf vollständig gesendet", flush=True)

        deadline = None if seconds is None else started_at + seconds
        try:
            while deadline is None or monotonic() < deadline:
                if stop_requested is not None and stop_requested():
                    break
                now = monotonic()
                if now >= next_heartbeat:
                    client.send_ping()
                    next_heartbeat = now + heartbeat_interval
                if progress_callback is not None and now >= next_progress:
                    progress_callback(
                        LiveListenProgress(
                            elapsed_seconds=now - started_at,
                            datagrams=datagrams,
                            target_voice_bursts=voice,
                            decoded_codewords=codewords,
                            decode_errors=decode_errors,
                            corrected_errors=corrected,
                            concealed_bursts=concealed,
                            invalid_dmrd=invalid,
                        )
                    )
                    next_progress = now + progress_interval
                if now >= next_diagnostic_summary:
                    print(
                        "[DIAG][STAT] "
                        f"UDP={datagrams} DMRD-Voice={voice} Header={headers} "
                        f"Terminator={terminators} Codewörter={codewords} "
                        f"Audio-Schreibvorgänge={audio_writes} Audio-Samples={audio_samples} "
                        f"Decoderfehler={decode_errors} Ungültig={invalid} "
                        f"Verworfen(TG={rejected_tg},TS={rejected_ts},"
                        f"Rufart={rejected_call_type},Frame={rejected_frame}) "
                        f"PONG={pongs} Sonstige={non_dmrd}",
                        flush=True,
                    )
                    next_diagnostic_summary = now + DIAGNOSTIC_SUMMARY_INTERVAL_SECONDS

                try:
                    datagram = client.transport.receive()
                except NetworkReceiveTimeout:
                    continue
                datagrams += 1
                if is_master_pong(datagram, config.dmr_id):
                    pongs += 1
                    continue
                if not datagram.startswith(b"DMRD"):
                    non_dmrd += 1
                    print(
                        f"[DIAG][RX] Sonstiges UDP-Paket: {len(datagram)} Byte, "
                        f"Start={datagram[:12].hex(' ')}",
                        flush=True,
                    )
                    continue
                try:
                    packet = parse_dmrd_packet(datagram)
                except (TypeError, ValueError) as error:
                    invalid += 1
                    print(
                        f"[DIAG][DMRD] Ungültiges Paket ({len(datagram)} Byte): {error}",
                        flush=True,
                    )
                    continue
                frame_name = (
                    f"VOICE-{packet.voice_frame_number}"
                    if packet.frame_class is DmrdFrameClass.VOICE
                    else packet.frame_class.name
                )
                print(
                    f"[DIAG][DMRD] Seq={packet.sequence:03d} Src={packet.source_id} "
                    f"Dst={packet.destination_id} TS{packet.timeslot} "
                    f"Ruf={packet.call_type.name} Frame={frame_name} "
                    f"Stream={packet.stream_id:08X}",
                    flush=True,
                )
                if packet.destination_id != target_talkgroup:
                    rejected_tg += 1
                    print(
                        f"[DIAG][FILTER] VERWORFEN: TG {packet.destination_id} "
                        f"statt TG {target_talkgroup}",
                        flush=True,
                    )
                    continue
                if packet.timeslot != target_timeslot:
                    rejected_ts += 1
                    print(
                        f"[DIAG][FILTER] VERWORFEN: TS{packet.timeslot} "
                        f"statt TS{target_timeslot}",
                        flush=True,
                    )
                    continue
                expected_call_type = "PRIVATE" if target_call_type == "private" else "GROUP"
                if packet.call_type.name != expected_call_type:
                    rejected_call_type += 1
                    print(f"[DIAG][FILTER] VERWORFEN: Rufart {packet.call_type.name} statt {expected_call_type}", flush=True)
                    continue
                print("[DIAG][FILTER] AKZEPTIERT: TG, Timeslot und Rufart passen", flush=True)
                if packet.is_voice_lc_header:
                    headers += 1
                    print("[DIAG][FRAME] Voice-LC-Header erkannt; Decoder wird zurückgesetzt", flush=True)
                    if call_activity_callback is not None:
                        call_activity_callback(
                            LiveCallActivity(
                                True, packet.source_id, packet.destination_id,
                                packet.timeslot, packet.stream_id or None,
                            )
                        )
                    decoder.close()
                    decoder = decoder_factory()
                    jitter.reset(first_voice_sequence=(packet.sequence + 1) & 0xFF)
                    continue
                if packet.is_terminator_with_lc:
                    terminators += 1
                    print("[DIAG][FRAME] Terminator mit LC erkannt", flush=True)
                    if call_activity_callback is not None:
                        call_activity_callback(
                            LiveCallActivity(
                                False, packet.source_id, packet.destination_id,
                                packet.timeslot, packet.stream_id or None,
                            )
                        )
                    batch = jitter.flush()
                    for frame in batch.frames:
                        if output_muted is None or not output_muted():
                            output.write(frame)
                            samples += len(frame)
                            audio_writes += 1
                            audio_samples += len(frame)
                            print(f"[DIAG][AUDIO] {len(frame)} PCM-Samples geschrieben", flush=True)
                    concealed += batch.concealed_bursts
                    jitter.reset()
                    continue
                if packet.frame_class not in (
                    DmrdFrameClass.VOICE,
                    DmrdFrameClass.VOICE_SYNC,
                ):
                    rejected_frame += 1
                    print("[DIAG][FILTER] VERWORFEN: kein Sprachrahmen", flush=True)
                    continue

                if call_activity_callback is not None:
                    call_activity_callback(
                        LiveCallActivity(
                            True, packet.source_id, packet.destination_id,
                            packet.timeslot, packet.stream_id or None,
                        )
                    )
                voice += 1
                decoded: list[int] = []
                try:
                    for word in extract_ambe_codewords(packet):
                        frame = decoder.decode(word)
                        decoded.extend(frame.samples)
                        codewords += 1
                        corrected += frame.corrected_errors
                except Exception as error:
                    decode_errors += 1
                    print(
                        f"[DIAG][DECODER] FEHLER {type(error).__name__}: {error}",
                        flush=True,
                    )
                    continue
                print(
                    f"[DIAG][DECODER] 3 AMBE-Codewörter -> {len(decoded)} PCM-Samples",
                    flush=True,
                )

                batch = jitter.push(packet.sequence, tuple(decoded))
                for frame in batch.frames:
                    if output_muted is None or not output_muted():
                        output.write(frame)
                        samples += len(frame)
                        audio_writes += 1
                        audio_samples += len(frame)
                        print(f"[DIAG][AUDIO] {len(frame)} PCM-Samples geschrieben", flush=True)
                concealed += batch.concealed_bursts
        except KeyboardInterrupt:
            interrupted = True

        batch = jitter.flush()
        for frame in batch.frames:
            if output_muted is None or not output_muted():
                output.write(frame)
                samples += len(frame)
                audio_writes += 1
                audio_samples += len(frame)
                print(f"[DIAG][AUDIO] {len(frame)} PCM-Samples geschrieben (Restpuffer)", flush=True)
        concealed += batch.concealed_bursts
        sleep(0.25)
        print(
            "[DIAG][ENDE] "
            f"UDP={datagrams} Voice={voice} Header={headers} Terminator={terminators} "
            f"Codewörter={codewords} Audio-Schreibvorgänge={audio_writes} "
            f"Audio-Samples={audio_samples} Decoderfehler={decode_errors} "
            f"Ungültig={invalid} Verworfen(TG={rejected_tg},TS={rejected_ts},"
            f"Rufart={rejected_call_type},Frame={rejected_frame})",
            flush=True,
        )
    finally:
        elapsed = max(0.0, monotonic() - started_at)
        if decoder is not None:
            decoder.close()
        client.close()
        output.close()
        closed = (
            client.transport is None
            and client.state is LoginState.DISCONNECTED
            and not output.is_open
        )

    return LiveListenResult(
        authenticated=authenticated,
        audio_started=audio_started,
        synthetic_samples=synthetic_count,
        elapsed_seconds=elapsed,
        datagrams=datagrams,
        target_voice_bursts=voice,
        decoded_codewords=codewords,
        decoded_samples=samples,
        decode_errors=decode_errors,
        corrected_errors=corrected,
        concealed_bursts=concealed,
        invalid_dmrd=invalid,
        interrupted=interrupted,
        closed=closed,
    )
