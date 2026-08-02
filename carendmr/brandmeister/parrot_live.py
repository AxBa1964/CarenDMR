"""Exactly-once live executor for the hard-locked private Parrot profile."""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass

from carendmr.accessibility import ParrotTestAnnouncer, ParrotTestPhase
from carendmr.audio import BufferedPcmOutput
from carendmr.network import NetworkReceiveTimeout
from carendmr.vocoder import NativeMbeReceiveVocoder, extract_ambe_codewords
from carendmr.vocoder.playout import DmrJitterBuffer

from .client import BrandMeisterClient
from .config import BrandMeisterConfig
from .dmrd import DmrdCallType, DmrdFrameClass, parse_dmrd_packet
from .parrot_profile import (
    PARROT_DESTINATION_ID,
    PARROT_ECHO_CAP_SECONDS,
    PARROT_TRANSMIT_CAP_SECONDS,
    ParrotSafetyError,
    build_locked_parrot_test_plan,
    validate_parrot_test_plan,
)
from .protocol import LoginState


PACKET_INTERVAL_SECONDS = 0.060


@dataclass(frozen=True, slots=True)
class ParrotLiveResult:
    authenticated: bool
    sent_packets: int
    transmit_elapsed_seconds: float
    echo_voice_bursts: int
    decoded_codewords: int
    output_samples: int
    decode_errors: int
    invalid_dmrd: int
    echo_received: bool
    timed_out: bool
    closed: bool


class ParrotLiveError(RuntimeError):
    """Fail-closed live result without sensitive fields."""

    def __init__(self, *, sent_packets: int, closed: bool, cause_name: str):
        super().__init__("Der verriegelte Parrot-Test wurde sicher abgebrochen.")
        self.sent_packets = sent_packets
        self.closed = closed
        self.cause_name = cause_name


def execute_locked_parrot_once(
    config: BrandMeisterConfig,
    *,
    announcer: ParrotTestAnnouncer,
    client_factory=BrandMeisterClient,
    output_factory=BufferedPcmOutput,
    decoder_factory=NativeMbeReceiveVocoder,
    sequence_factory=lambda: secrets.randbelow(256),
    stream_factory=lambda: secrets.randbelow(0xFFFFFFFF) + 1,
    monotonic=time.monotonic,
    sleep=time.sleep,
) -> ParrotLiveResult:
    """Run the one allowed private test; target/times/call type are not inputs."""

    if config.dmr_id > 0xFFFFFF:
        raise ParrotSafetyError("Die konfigurierte DMR-ID passt nicht in das Quellfeld.")

    plan = build_locked_parrot_test_plan(
        source_id=config.dmr_id,
        repeater_id=config.dmr_id,
        stream_id=stream_factory(),
        first_sequence=sequence_factory(),
    )
    validate_parrot_test_plan(plan)

    client = client_factory(config)
    output = output_factory(sample_rate=8000)
    decoder = None
    jitter = DmrJitterBuffer()
    authenticated = False
    sent = voice = codewords = output_samples = decode_errors = invalid = 0
    tx_elapsed = 0.0
    echo_received = timed_out = closed = False
    error: Exception | None = None

    try:
        announcer.announce(ParrotTestPhase.START)
        output.start()
        decoder = decoder_factory()
        client.login()
        authenticated = client.state is LoginState.CONNECTED
        if not authenticated or client.transport is None:
            raise ParrotSafetyError("Die Anmeldung ist nicht eindeutig verbunden.")

        announcer.announce(ParrotTestPhase.TRANSMIT)
        tx_start = monotonic()
        for index, packet in enumerate(plan.fixture.packets):
            validate_parrot_test_plan(plan)
            if monotonic() - tx_start >= PARROT_TRANSMIT_CAP_SECONDS:
                raise ParrotSafetyError("Die harte Sendezeitgrenze wurde erreicht.")
            raw = packet.to_bytes()
            if (
                packet.destination_id != PARROT_DESTINATION_ID
                or packet.timeslot != 2
                or packet.call_type is not DmrdCallType.PRIVATE
                or not raw[15] & 0x40
            ):
                raise ParrotSafetyError("Die private Parrot-Verriegelung ist verletzt.")
            written = client.transport.send(raw)
            if written != len(raw):
                raise ParrotSafetyError("Ein Parrot-Paket wurde nicht vollständig gesendet.")
            sent += 1
            if index + 1 < len(plan.fixture.packets):
                sleep(PACKET_INTERVAL_SECONDS)
        tx_elapsed = monotonic() - tx_start
        if tx_elapsed > PARROT_TRANSMIT_CAP_SECONDS:
            raise ParrotSafetyError("Die Übertragung überschritt fünfzehn Sekunden.")

        echo_start = monotonic()
        announcer.announce(ParrotTestPhase.ECHO)
        while True:
            remaining = PARROT_ECHO_CAP_SECONDS - (monotonic() - echo_start)
            if remaining <= 0:
                break
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
                invalid += 1
                continue
            if (
                packet.call_type is not DmrdCallType.PRIVATE
                or packet.timeslot != 2
                or PARROT_DESTINATION_ID
                not in (packet.source_id, packet.destination_id)
            ):
                continue
            if packet.is_voice_lc_header:
                decoder.close()
                decoder = decoder_factory()
                jitter.reset(first_voice_sequence=(packet.sequence + 1) & 0xFF)
                continue
            if packet.is_terminator_with_lc:
                batch = jitter.flush()
                for frame in batch.frames:
                    output.write(frame)
                    output_samples += len(frame)
                if voice:
                    echo_received = True
                break
            if packet.frame_class not in (
                DmrdFrameClass.VOICE,
                DmrdFrameClass.VOICE_SYNC,
            ):
                continue

            voice += 1
            decoded: list[int] = []
            try:
                for word in extract_ambe_codewords(packet):
                    frame = decoder.decode(word)
                    decoded.extend(frame.samples)
                    codewords += 1
            except Exception:
                decode_errors += 1
                continue
            batch = jitter.push(packet.sequence, tuple(decoded))
            for frame in batch.frames:
                output.write(frame)
                output_samples += len(frame)

        timed_out = not echo_received
        announcer.announce(
            ParrotTestPhase.TIMEOUT if timed_out else ParrotTestPhase.SUCCESS
        )
        sleep(0.25)
    except Exception as caught:
        error = caught
        try:
            announcer.announce(ParrotTestPhase.FAILURE)
        except Exception:
            pass
    finally:
        if decoder is not None:
            decoder.close()
        client.close()
        output.close()
        closed = (
            client.transport is None
            and client.state is LoginState.DISCONNECTED
            and not output.is_open
        )

    if error is not None:
        raise ParrotLiveError(
            sent_packets=sent,
            closed=closed,
            cause_name=type(error).__name__,
        ) from error

    return ParrotLiveResult(
        authenticated=authenticated,
        sent_packets=sent,
        transmit_elapsed_seconds=tx_elapsed,
        echo_voice_bursts=voice,
        decoded_codewords=codewords,
        output_samples=output_samples,
        decode_errors=decode_errors,
        invalid_dmrd=invalid,
        echo_received=echo_received,
        timed_out=timed_out,
        closed=closed,
    )
