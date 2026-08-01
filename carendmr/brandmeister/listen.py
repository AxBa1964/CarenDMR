"""Receive-only TG91/TS2 decode and audio playout."""

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
from .protocol import LoginState


MAX_LISTEN_SECONDS = 3600.0
DEFAULT_PROGRESS_INTERVAL_SECONDS = 30.0


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
    progress_callback: Callable[[LiveListenProgress], None] | None = None,
    progress_interval: float = DEFAULT_PROGRESS_INTERVAL_SECONDS,
    stop_requested: Callable[[], bool] | None = None,
    client_factory=BrandMeisterClient,
    output_factory=BufferedPcmOutput,
    decoder_factory=NativeMbeReceiveVocoder,
    monotonic=time.monotonic,
    sleep=time.sleep,
) -> LiveListenResult:
    """Authenticate and receive/decode/play until timeout or Ctrl+C."""

    if seconds is not None and (seconds <= 0 or seconds > MAX_LISTEN_SECONDS):
        raise ValueError("Die Empfangsdauer muss zwischen 1 und 3600 Sekunden liegen.")
    if progress_interval <= 0:
        raise ValueError("Das Diagnoseintervall muss größer als null sein.")

    client = client_factory(config)
    output = output_factory(sample_rate=8000)
    decoder = None
    jitter = DmrJitterBuffer()
    authenticated = audio_started = closed = interrupted = False
    synthetic_count = datagrams = voice = codewords = samples = 0
    decode_errors = corrected = concealed = invalid = 0
    started_at = monotonic()
    next_progress = started_at + progress_interval

    try:
        output.start()
        audio_started = True
        synthetic = _synthetic_samples()
        output.write(synthetic)
        synthetic_count = len(synthetic)
        sleep(0.25)

        decoder = decoder_factory()
        client.login()
        authenticated = client.state is LoginState.CONNECTED
        if not authenticated or client.transport is None:
            raise RuntimeError("Die Empfangsverbindung ist nicht eindeutig aktiv.")

        deadline = None if seconds is None else started_at + seconds
        try:
            while deadline is None or monotonic() < deadline:
                if stop_requested is not None and stop_requested():
                    break
                now = monotonic()
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
                if not datagram.startswith(b"DMRD"):
                    continue
                try:
                    packet = parse_dmrd_packet(datagram)
                except (TypeError, ValueError):
                    invalid += 1
                    continue
                if not packet.is_target_group:
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
                        samples += len(frame)
                    concealed += batch.concealed_bursts
                    jitter.reset()
                    continue
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
                        corrected += frame.corrected_errors
                except Exception:
                    decode_errors += 1
                    continue

                batch = jitter.push(packet.sequence, tuple(decoded))
                for frame in batch.frames:
                    output.write(frame)
                    samples += len(frame)
                concealed += batch.concealed_bursts
        except KeyboardInterrupt:
            interrupted = True

        batch = jitter.flush()
        for frame in batch.frames:
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
