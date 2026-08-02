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

    try:
        output.start()
        audio_started = True
        synthetic = _synthetic_samples()
        if output_muted is None or not output_muted():
            output.write(synthetic)
        synthetic_count = len(synthetic)
        sleep(0.25)

        decoder = decoder_factory()
        client.login()
        authenticated = client.state is LoginState.CONNECTED
        if not authenticated or client.transport is None:
            raise RuntimeError("Die Empfangsverbindung ist nicht eindeutig aktiv.")

        activate_dynamic_talkgroup(
            client.transport,
            dmr_id=config.dmr_id,
            talkgroup=target_talkgroup,
            timeslot=target_timeslot,
        )

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

                try:
                    datagram = client.transport.receive()
                except NetworkReceiveTimeout:
                    continue
                datagrams += 1
                if is_master_pong(datagram, config.dmr_id):
                    continue
                if not datagram.startswith(b"DMRD"):
                    continue
                try:
                    packet = parse_dmrd_packet(datagram)
                except (TypeError, ValueError):
                    invalid += 1
                    continue
                if not packet.matches_group_target(target_talkgroup, target_timeslot):
                    continue
                if packet.is_voice_lc_header:
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
                    concealed += batch.concealed_bursts
                    jitter.reset()
                    continue
                if packet.frame_class not in (
                    DmrdFrameClass.VOICE,
                    DmrdFrameClass.VOICE_SYNC,
                ):
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
                except Exception:
                    decode_errors += 1
                    continue

                batch = jitter.push(packet.sequence, tuple(decoded))
                for frame in batch.frames:
                    if output_muted is None or not output_muted():
                        output.write(frame)
                        samples += len(frame)
                concealed += batch.concealed_bursts
        except KeyboardInterrupt:
            interrupted = True

        batch = jitter.flush()
        for frame in batch.frames:
            if output_muted is None or not output_muted():
                output.write(frame)
                samples += len(frame)
        concealed += batch.concealed_bursts
        sleep(0.25)
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
