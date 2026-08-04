"""Echter DMR-Live-Sendepfad: PCM wird während gedrückter PTT codiert und gesendet."""
from __future__ import annotations

import ctypes
import math
import os
import secrets
import time
import wave
import array
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Iterable

from carendmr.audio import BufferedPcmOutput
from carendmr.encoder import AmbeEncoder
from carendmr.network import NetworkReceiveTimeout
from carendmr.vocoder import NativeMbeReceiveVocoder, extract_ambe_codewords
from carendmr.vocoder.playout import DmrJitterBuffer
from carendmr.diagnostics.tx_rx_timing import mark as timing_mark

from .client import BrandMeisterClient
from .config import BrandMeisterConfig
from .dmrd import DmrdCallType, DmrdDataType, DmrdFrameClass, DmrdPacket, parse_dmrd_packet
from .parrot_profile import PARROT_ECHO_CAP_SECONDS, PARROT_TRANSMIT_CAP_SECONDS, ParrotSafetyError
from .protocol import LoginState
from .silent_call import _MS_AUDIO_SYNC, _add_sync, _bits_to_bytes, _encode_embedded_lc, _encode_full_lc_burst, _EMB_CODEWORDS
from .voice_transmit import VoiceTransmitResult, _pack_ambe, _apply_embedded_lc, PCM_FRAME_SAMPLES, PACKET_INTERVAL_SECONDS



class _WindowsTimerResolution:
    """Aktiviert unter Windows während TX eine 1-ms-Timerauflösung."""

    def __init__(self, milliseconds: int = 1) -> None:
        self._milliseconds = milliseconds
        self._active = False

    def __enter__(self):
        if os.name == "nt":
            try:
                winmm = ctypes.WinDLL("winmm")
                self._active = winmm.timeBeginPeriod(self._milliseconds) == 0
            except (AttributeError, OSError):
                self._active = False
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._active:
            try:
                ctypes.WinDLL("winmm").timeEndPeriod(self._milliseconds)
            except (AttributeError, OSError):
                pass


def _wait_until(deadline: float, *, monotonic, sleep) -> None:
    """Wartet grob per sleep und die letzten 1,5 ms hochauflösend.

    Windows' normaler Scheduler kann sleep-Aufrufe sonst in rund 15,6-ms-
    Schritten auflösen. Die kurze Endphase verhindert die gemessenen
    46/79-ms-Burstabstände, ohne einen CPU-Kern über die gesamte 60-ms-
    Periode zu beschäftigen.
    """
    while True:
        remaining = deadline - monotonic()
        if remaining <= 0:
            return
        if remaining > 0.0015:
            sleep(max(0.0, remaining - 0.0015))
            continue
        # Nur die letzten maximal 1,5 ms präzise warten. sleep(0) gibt
        # anderen Threads Gelegenheit, ohne erneut einen langen Timer zu setzen.
        if remaining > 0.00025:
            sleep(0)


def _packet(*, sequence, source_id, destination_id, repeater_id, timeslot, call_type,
            frame_class, stream_id, payload, voice_no=None, data_type=None):
    return DmrdPacket(sequence, source_id, destination_id, repeater_id, timeslot,
                      call_type, frame_class, stream_id, payload,
                      voice_frame_number=voice_no, data_type=data_type)


def execute_live_voice_once(
    config: BrandMeisterConfig, *, destination_id: int, timeslot: int,
    call_type: DmrdCallType, pcm_chunks: Iterable[tuple[int, ...]], encoder: AmbeEncoder,
    wait_for_parrot_echo: bool = False, lead_in_seconds: float = 0.240,
    client_factory=BrandMeisterClient, output_factory=BufferedPcmOutput,
    decoder_factory=NativeMbeReceiveVocoder, monotonic=time.monotonic, sleep=time.sleep,
    rx_debug_dir: Path | None = None, rx_playback_gate=None,
) -> VoiceTransmitResult:
    """Sendet PCM fortlaufend. Nach Ende des Iterators folgen nur Pad/Terminator."""
    source_id = config.dmr_id
    stream_id = secrets.randbelow(0xFFFFFFFF) + 1
    sequence = secrets.randbelow(256)
    flco = 0x03 if call_type is DmrdCallType.PRIVATE else 0x00
    lc = bytes((flco, 0, 0)) + destination_id.to_bytes(3, 'big') + source_id.to_bytes(3, 'big')
    embedded = _encode_embedded_lc(lc)
    client = client_factory(config)
    output = output_factory(sample_rate=8000) if wait_for_parrot_echo else None
    decoder = None
    jitter = DmrJitterBuffer()
    sent = voice = echo_voice = decoded_words = output_samples = decode_errors = 0
    authenticated = closed = echo_received = timed_out = False
    tx_start = 0.0
    next_send = 0.0
    late_schedule_resets = 0
    send_times: list[float] = []
    schedule_errors_ms: list[float] = []
    encoder_times_ms: list[float] = []
    early_bursts = late_bursts = 0
    rx_debug_samples: list[int] = []
    rx_debug_path: Path | None = None
    pending_rx_frames: list[tuple[int, ...]] = []

    def play_rx_frame(frame) -> None:
        nonlocal output_samples
        samples = tuple(int(sample) for sample in frame)
        if rx_playback_gate is not None and not rx_playback_gate.is_set():
            pending_rx_frames.append(samples)
            return
        if pending_rx_frames:
            for buffered in pending_rx_frames:
                output.write(buffered); output_samples += len(buffered)
                rx_debug_samples.extend(buffered)
            pending_rx_frames.clear()
        output.write(samples); output_samples += len(samples)
        rx_debug_samples.extend(samples)

    def flush_rx_frames() -> None:
        if rx_playback_gate is not None:
            rx_playback_gate.wait(timeout=3.0)
        if output is not None:
            for buffered in pending_rx_frames:
                output.write(buffered)
                rx_debug_samples.extend(buffered)
            pending_rx_frames.clear()

    def send_packet(packet: DmrdPacket, *, paced: bool = True) -> None:
        nonlocal sent, voice, next_send, late_schedule_resets, early_bursts, late_bursts
        scheduled = None
        if paced:
            now = monotonic()
            if not next_send:
                next_send = now
            scheduled = next_send
            delay = next_send - now
            if delay > 0:
                _wait_until(next_send, monotonic=monotonic, sleep=sleep)
            elif delay < -0.250:
                # Nach einer echten Blockade nicht in einem unkontrollierten Burst
                # mehrere alte Zeitmarken nachholen. Kleine Encoder-/Scheduler-
                # Abweichungen werden dagegen durch den absoluten Takt aufgeholt.
                next_send = now
                late_schedule_resets += 1
        actual_send = monotonic()
        if paced and scheduled is not None:
            error_ms = (actual_send - scheduled) * 1000.0
            schedule_errors_ms.append(error_ms)
            if error_ms < -2.0: early_bursts += 1
            elif error_ms > 2.0: late_bursts += 1
            send_times.append(actual_send)
        raw = packet.to_bytes()
        if client.transport is None or client.transport.send(raw) != len(raw):
            raise RuntimeError('Ein DMRD-Paket wurde nicht vollständig gesendet.')
        sent += 1
        if sent == 1:
            timing_mark('TX_ERSTER_FRAME_GESENDET')
        if packet.frame_class in (DmrdFrameClass.VOICE, DmrdFrameClass.VOICE_SYNC):
            voice += 1
        if paced:
            # Absoluter 60-ms-Takt: Encoder-, Python- und Socket-Laufzeit werden
            # nicht bei jedem Burst zusätzlich auf die Sendedauer aufgeschlagen.
            next_send += PACKET_INTERVAL_SECONDS

    timer_resolution = _WindowsTimerResolution(1)
    timer_resolution.__enter__()
    try:
        if output is not None:
            output.start()
            decoder = decoder_factory()
        timing_mark('TX_LOGIN_START')
        client.login()
        timing_mark('TX_LOGIN_FERTIG')
        authenticated = client.state is LoginState.CONNECTED
        if not authenticated or client.transport is None:
            raise RuntimeError('BrandMeister-Anmeldung fehlgeschlagen.')
        tx_start = monotonic()
        timing_mark('TX_ERSTER_FRAME_START')
        header = _packet(sequence=sequence, source_id=source_id, destination_id=destination_id,
                         repeater_id=source_id, timeslot=timeslot, call_type=call_type,
                         frame_class=DmrdFrameClass.DATA_SYNC, stream_id=stream_id,
                         payload=_encode_full_lc_burst(lc, 0x01),
                         data_type=DmrdDataType.VOICE_LC_HEADER.value)
        send_packet(header, paced=False)
        sequence = (sequence + 1) & 0xFF

        pcm_buffer = [0] * int(round(8000 * lead_in_seconds))
        ambe_frames: list[bytes] = []
        burst_number = 0

        def drain(final: bool = False) -> None:
            nonlocal sequence, burst_number
            while len(pcm_buffer) >= PCM_FRAME_SAMPLES or (final and pcm_buffer):
                frame = tuple(pcm_buffer[:PCM_FRAME_SAMPLES])
                del pcm_buffer[:PCM_FRAME_SAMPLES]
                if len(frame) < PCM_FRAME_SAMPLES:
                    frame += (0,) * (PCM_FRAME_SAMPLES - len(frame))
                encode_started = monotonic()
                word = encoder.encode_2450x1150(frame)
                encoder_times_ms.append((monotonic() - encode_started) * 1000.0)
                if len(word) != 9:
                    raise ParrotSafetyError('Der Encoder lieferte keinen 9-Byte-AMBE-Rahmen.')
                ambe_frames.append(word)
                if len(ambe_frames) == 3:
                    burst = _pack_ambe(tuple(ambe_frames))
                    number = burst_number % 6
                    if number == 0:
                        _add_sync(burst, _MS_AUDIO_SYNC)
                        frame_class = DmrdFrameClass.VOICE_SYNC
                        voice_no = None
                    else:
                        _apply_embedded_lc(burst, number, embedded)
                        frame_class = DmrdFrameClass.VOICE
                        voice_no = number
                    packet = _packet(sequence=sequence, source_id=source_id,
                                     destination_id=destination_id, repeater_id=source_id,
                                     timeslot=timeslot, call_type=call_type,
                                     frame_class=frame_class, stream_id=stream_id,
                                     payload=bytes(burst), voice_no=voice_no)
                    send_packet(packet)
                    sequence = (sequence + 1) & 0xFF
                    burst_number += 1
                    ambe_frames.clear()

        # Die ersten während des RX-Abbaus gepufferten Chunks werden nach Login
        # zügig, aber mit korrektem 60-ms-DMR-Takt abgearbeitet.
        for chunk in pcm_chunks:
            if monotonic() - tx_start >= PARROT_TRANSMIT_CAP_SECONDS:
                raise RuntimeError('Die Sendezeitgrenze wurde erreicht.')
            pcm_buffer.extend(chunk)
            drain()
        drain(final=True)
        timing_mark("TX_LETZTER_AMBE_FRAME_CODIERT", f"Restframes={len(ambe_frames)}")
        while ambe_frames:
            encode_started = monotonic()
            pad_word = encoder.encode_2450x1150((0,) * PCM_FRAME_SAMPLES)
            encoder_times_ms.append((monotonic() - encode_started) * 1000.0)
            ambe_frames.append(pad_word)
            if len(ambe_frames) == 3:
                burst = _pack_ambe(tuple(ambe_frames))
                number = burst_number % 6
                if number == 0:
                    _add_sync(burst, _MS_AUDIO_SYNC); frame_class = DmrdFrameClass.VOICE_SYNC; voice_no = None
                else:
                    _apply_embedded_lc(burst, number, embedded); frame_class = DmrdFrameClass.VOICE; voice_no = number
                send_packet(_packet(sequence=sequence, source_id=source_id, destination_id=destination_id,
                                    repeater_id=source_id, timeslot=timeslot, call_type=call_type,
                                    frame_class=frame_class, stream_id=stream_id,
                                    payload=bytes(burst), voice_no=voice_no))
                sequence = (sequence + 1) & 0xFF
                ambe_frames.clear()
        intervals_ms = [(b-a)*1000.0 for a,b in zip(send_times, send_times[1:])]
        def _stats(values: list[float]) -> tuple[float,float,float,float]:
            if not values: return (0.0,0.0,0.0,0.0)
            avg=sum(values)/len(values); rms=math.sqrt(sum((v-avg)**2 for v in values)/len(values))
            return avg,min(values),max(values),rms
        int_avg,int_min,int_max,int_rms=_stats(intervals_ms)
        enc_avg,enc_min,enc_max,enc_rms=_stats(encoder_times_ms)
        err_avg,err_min,err_max,err_rms=_stats(schedule_errors_ms)
        timing_mark("TX_JITTER_STATISTIK", f"Bursts={len(send_times)};AbstandAvgMs={int_avg:.3f};MinMs={int_min:.3f};MaxMs={int_max:.3f};JitterRmsMs={int_rms:.3f};SollFehlerAvgMs={err_avg:.3f};MinMs={err_min:.3f};MaxMs={err_max:.3f};RmsMs={err_rms:.3f};ZuFrueh={early_bursts};ZuSpaet={late_bursts};TaktResets={late_schedule_resets}")
        timing_mark("TX_ENCODER_STATISTIK", f"Frames={len(encoder_times_ms)};AvgMs={enc_avg:.3f};MinMs={enc_min:.3f};MaxMs={enc_max:.3f};RmsMs={enc_rms:.3f}")
        timing_mark("TX_LETZTER_VOICE_FRAME_GESENDET", f"VoiceBursts={voice};TaktResets={late_schedule_resets}")
        terminator = _packet(sequence=sequence, source_id=source_id, destination_id=destination_id,
                             repeater_id=source_id, timeslot=timeslot, call_type=call_type,
                             frame_class=DmrdFrameClass.DATA_SYNC, stream_id=stream_id,
                             payload=_encode_full_lc_burst(lc, 0x02),
                             data_type=DmrdDataType.TERMINATOR_WITH_LC.value)
        send_packet(terminator)
        timing_mark("TX_TERMINATOR_GESENDET")
        timing_mark('TX_LETZTER_FRAME_GESENDET')
        tx_elapsed = monotonic() - tx_start

        if wait_for_parrot_echo:
            timing_mark("PARROT_ECHO_WARTE_START")
            echo_start = monotonic()
            first_echo_packet_marked = False
            while monotonic() - echo_start < PARROT_ECHO_CAP_SECONDS:
                remaining = PARROT_ECHO_CAP_SECONDS - (monotonic() - echo_start)
                if hasattr(client.transport, 'set_receive_timeout'):
                    client.transport.set_receive_timeout(min(0.5, remaining))
                try:
                    datagram = client.transport.receive()
                except NetworkReceiveTimeout:
                    continue
                if not datagram.startswith(b'DMRD'):
                    continue
                if not first_echo_packet_marked:
                    timing_mark("PARROT_ERSTES_DMRD_PAKET")
                    first_echo_packet_marked = True
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
                    for frame in jitter.flush().frames:
                        play_rx_frame(frame)
                    echo_received = echo_voice > 0
                    timing_mark("PARROT_TERMINATOR_EMPFANGEN", f"VoiceBursts={echo_voice}")
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
                for frame in jitter.push(packet.sequence, tuple(decoded)).frames:
                    play_rx_frame(frame)
            flush_rx_frames()
            timed_out = not echo_received
            timing_mark("PARROT_ECHO_WARTE_ENDE", "Timeout" if timed_out else "Echo vollständig")
            if rx_debug_dir is not None and rx_debug_samples:
                rx_debug_dir = Path(rx_debug_dir)
                rx_debug_dir.mkdir(parents=True, exist_ok=True)
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                rx_debug_path = rx_debug_dir / f"rx_{stamp}_03_parrot_nach_ambe_8k.wav"
                pcm = array.array("h", rx_debug_samples)
                import sys
                if sys.byteorder != "little":
                    pcm.byteswap()
                with wave.open(str(rx_debug_path), "wb") as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(8000)
                    wav_file.writeframes(pcm.tobytes())
                timing_mark("RX_AUDIO_DEBUG_WAV", f"ParrotNachAMBE8k={rx_debug_path};Samples={len(rx_debug_samples)}")
        return VoiceTransmitResult(authenticated, sent, voice, tx_elapsed, False,
                                   echo_received, echo_voice, timed_out,
                                   decoded_words, output_samples, decode_errors)
    finally:
        timer_resolution.__exit__(None, None, None)
        if decoder is not None:
            decoder.close()
        client.close()
        if output is not None:
            output.close()
        timing_mark('TX_VERBINDUNG_GESCHLOSSEN')
