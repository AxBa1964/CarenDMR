"""Echter DMR-Live-Sendepfad: PCM wird während gedrückter PTT codiert und gesendet."""
from __future__ import annotations
from carendmr.diagnostics.wav_io import write_pcm16_mono

import ctypes
import math
import os
import platform
import secrets
import time
import wave
import array
import queue
import threading
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Callable, Iterable

from carendmr.audio import BufferedPcmOutput
from carendmr.encoder import AmbeEncoder
from carendmr.network import NetworkReceiveTimeout
from carendmr.vocoder import NativeMbeReceiveVocoder, extract_ambe_codewords
from carendmr.vocoder.playout import DmrJitterBuffer
from carendmr.diagnostics.tx_rx_timing import mark as timing_mark, detach_session as timing_detach_session
from carendmr.diagnostics.audio_report_worker import schedule_session_report

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
    rx_debug_dir: Path | None = None, rx_playback_gate=None, ambe_debug_path: Path | None = None,
    tx_complete_callback: Callable[[], None] | None = None,
    existing_client: BrandMeisterClient | None = None,
    preserve_client: bool = False,
    defer_debug_report: bool = False,
) -> VoiceTransmitResult:
    """Sendet PCM fortlaufend. Nach Ende des Iterators folgen nur Pad/Terminator."""
    source_id = config.dmr_id
    stream_id = secrets.randbelow(0xFFFFFFFF) + 1
    sequence = 0 if platform.system() == "Darwin" else secrets.randbelow(256)
    flco = 0x03 if call_type is DmrdCallType.PRIVATE else 0x00
    lc = bytes((flco, 0, 0)) + destination_id.to_bytes(3, 'big') + source_id.to_bytes(3, 'big')
    embedded = _encode_embedded_lc(lc)
    client = existing_client or client_factory(config)
    output = output_factory(sample_rate=8000) if wait_for_parrot_echo else None
    decoder = None
    loopback_decoder = None
    loopback_samples: list[int] = []
    loopback_corrected_errors = 0
    loopback_decode_exceptions = 0
    loopback_frames = 0
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
    echo_stream_id: int | None = None
    rx_trace_limit = 24
    rx_trace_packets = 0
    rx_trace_parse_errors = 0
    rx_trace_filter_rejects = 0
    rx_trace_non_voice = 0
    rx_trace_voice_packets = 0
    rx_trace_decoded_frames = 0
    rx_trace_pcm_samples = 0

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
            # Der RX-Ausgabepfad wird vor Login und TX vollständig geöffnet.
            # Dadurch initialisiert nicht erst der erste Parrot-Stream zufällig
            # Decoder, Queue oder Audio-Backend.
            timing_mark("RX_INITIALISIERUNG_START")
            output.start()
            decoder = decoder_factory()
            jitter.reset()
            pending_rx_frames.clear()
            timing_mark("RX_INITIALISIERUNG_BEREIT")
        if ambe_debug_path is not None:
            try:
                loopback_decoder = decoder_factory()
            except Exception as exc:
                timing_mark("CODEC_LOOPBACK_NICHT_VERFUEGBAR", str(exc))
        if client.state is LoginState.CONNECTED and client.transport is not None:
            authenticated = True
            timing_mark('TX_SESSION_WIEDERVERWENDET', 'Bestehende BrandMeister-Verbindung')
        else:
            timing_mark('TX_LOGIN_START')
            client.login()
            timing_mark('TX_LOGIN_FERTIG')
            authenticated = client.state is LoginState.CONNECTED
        if not authenticated or client.transport is None:
            raise RuntimeError('BrandMeister-Anmeldung fehlgeschlagen.')
        tx_start = monotonic()
        timing_mark('TX_ERSTER_FRAME_START')
        timing_mark(
            "TX_STREAM_START",
            f"StreamID={stream_id:08X};Sequence={sequence};Src={source_id};"
            f"Dst={destination_id};TS={timeslot};CallType={call_type};"
            f"SequencePolicy={'zero-darwin' if platform.system() == 'Darwin' else 'random-existing'}",
        )
        header = _packet(sequence=sequence, source_id=source_id, destination_id=destination_id,
                         repeater_id=source_id, timeslot=timeslot, call_type=call_type,
                         frame_class=DmrdFrameClass.DATA_SYNC, stream_id=stream_id,
                         payload=_encode_full_lc_burst(lc, 0x01),
                         data_type=DmrdDataType.VOICE_LC_HEADER.value)
        droidstar_reference_timing = platform.system() == "Darwin"
        if droidstar_reference_timing:
            timing_mark(
                "TX_HEADER_MACOS_WARTET_AUF_PUFFER",
                "DroidStar-Referenz: LC-Header erst nach fertigem AMBE-Prebuffer",
            )
        else:
            # Bestehender Windows-/Nicht-macOS-Ablauf bleibt unverändert.
            send_packet(header, paced=False)
            sequence = (sequence + 1) & 0xFF

        # 0.2.1.22: PCM-Erfassung/MD380-Encoding vom 60-ms-Sendetakt entkoppeln.
        # Die 240-ms-TX-Vorlaufstille liefert zugleich einen Reservepuffer von
        # vier DMR-Voice-Bursts. Kurze Encoder-Ausreißer (im Feld bis 156 ms)
        # können dadurch abgefangen werden, ohne den Netz-Sendetakt zu zerreißen.
        pcm_frame_queue: queue.Queue[tuple[int, ...] | object] = queue.Queue(maxsize=256)
        encoded_queue: queue.Queue[bytes | object] = queue.Queue(maxsize=256)
        pipeline_end = object()
        pipeline_error: list[BaseException] = []
        feeder_done = threading.Event()
        encoder_done = threading.Event()
        encoder_queue_max = 0
        encoded_queue_max = 0
        pcm_frames_produced = 0

        def feeder_worker() -> None:
            nonlocal encoder_queue_max, pcm_frames_produced
            pcm_buffer = [0] * int(round(8000 * lead_in_seconds))
            try:
                for chunk in pcm_chunks:
                    if monotonic() - tx_start >= PARROT_TRANSMIT_CAP_SECONDS:
                        raise RuntimeError('Die Sendezeitgrenze wurde erreicht.')
                    pcm_buffer.extend(chunk)
                    while len(pcm_buffer) >= PCM_FRAME_SAMPLES:
                        frame = tuple(pcm_buffer[:PCM_FRAME_SAMPLES])
                        del pcm_buffer[:PCM_FRAME_SAMPLES]
                        pcm_frame_queue.put(frame)
                        pcm_frames_produced += 1
                        encoder_queue_max = max(encoder_queue_max, pcm_frame_queue.qsize())
                if pcm_buffer:
                    frame = tuple(pcm_buffer[:PCM_FRAME_SAMPLES])
                    if len(frame) < PCM_FRAME_SAMPLES:
                        frame += (0,) * (PCM_FRAME_SAMPLES - len(frame))
                    pcm_frame_queue.put(frame)
                    pcm_frames_produced += 1
                    encoder_queue_max = max(encoder_queue_max, pcm_frame_queue.qsize())
            except BaseException as error:
                pipeline_error.append(error)
            finally:
                feeder_done.set()
                pcm_frame_queue.put(pipeline_end)

        def encoder_worker() -> None:
            nonlocal loopback_corrected_errors, loopback_decode_exceptions, loopback_frames, encoded_queue_max
            first_frame = True
            try:
                while True:
                    item = pcm_frame_queue.get()
                    if item is pipeline_end:
                        break
                    frame = item
                    encode_started = monotonic()
                    if first_frame:
                        timing_mark("TX_ERSTES_PCM_FRAME", f"Samples={len(frame)};Min={min(frame)};Max={max(frame)}")
                    word = encoder.encode_2450x1150(frame)
                    encoder_times_ms.append((monotonic() - encode_started) * 1000.0)
                    if first_frame:
                        timing_mark("TX_ERSTES_AMBE_CODEWORT", f"Bytes={len(word)}")
                        first_frame = False
                    if len(word) != 9:
                        raise ParrotSafetyError('Der Encoder lieferte keinen 9-Byte-AMBE-Rahmen.')

                    if loopback_decoder is not None:
                        try:
                            decoded_loop = loopback_decoder.decode(word)
                            loopback_frames += 1
                            loopback_samples.extend(int(v) for v in decoded_loop.samples)
                            loopback_corrected_errors += max(0, int(decoded_loop.corrected_errors))
                            if loopback_frames == 1:
                                timing_mark(
                                    "CODEC_LOOPBACK_ERSTER_FRAME",
                                    f"KorrigierteBits={decoded_loop.corrected_errors};Samples={len(decoded_loop.samples)}",
                                )
                        except Exception as exc:
                            loopback_decode_exceptions += 1
                            timing_mark("CODEC_LOOPBACK_FEHLER", str(exc))

                    if ambe_debug_path is not None:
                        Path(ambe_debug_path).parent.mkdir(parents=True, exist_ok=True)
                        with Path(ambe_debug_path).open("ab") as ambe_file:
                            ambe_file.write(word)

                    encoded_queue.put(word)
                    encoded_queue_max = max(encoded_queue_max, encoded_queue.qsize())
            except BaseException as error:
                pipeline_error.append(error)
            finally:
                encoder_done.set()
                encoded_queue.put(pipeline_end)

        feeder_thread = threading.Thread(
            target=feeder_worker, name="CarenDMR-TX-PCM-Feeder", daemon=True
        )
        encoder_thread = threading.Thread(
            target=encoder_worker, name="CarenDMR-TX-MD380-Encoder", daemon=True
        )
        feeder_thread.start()
        encoder_thread.start()

        # Vier vollständige Bursts (240 ms) vorfüllen. Das entspricht genau dem
        # bestehenden TX-Lead-In und verändert den hörbaren Sprachbeginn nicht.
        prebuffer_words: list[bytes] = []
        while len(prebuffer_words) < 12:
            item = encoded_queue.get()
            if item is pipeline_end:
                break
            prebuffer_words.append(item)
        timing_mark(
            "TX_ENCODER_PUFFER_BEREIT",
            f"Codewords={len(prebuffer_words)};ReserveMs={len(prebuffer_words) * 20}",
        )

        if droidstar_reference_timing:
            send_packet(header, paced=False)
            sequence = (sequence + 1) & 0xFF
            next_send = monotonic() + PACKET_INTERVAL_SECONDS
            timing_mark(
                "TX_HEADER_MACOS_DROIDSTAR_REFERENZ",
                f"SequenceNaechsterFrame={sequence};"
                f"VoiceStartInMs={PACKET_INTERVAL_SECONDS * 1000.0:.1f}",
            )

        ambe_frames: list[bytes] = []
        burst_number = 0

        def send_word(word: bytes) -> None:
            nonlocal sequence, burst_number
            ambe_frames.append(word)
            if len(ambe_frames) < 3:
                return
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
            packet = _packet(
                sequence=sequence, source_id=source_id, destination_id=destination_id,
                repeater_id=source_id, timeslot=timeslot, call_type=call_type,
                frame_class=frame_class, stream_id=stream_id,
                payload=bytes(burst), voice_no=voice_no,
            )
            send_packet(packet)
            sequence = (sequence + 1) & 0xFF
            burst_number += 1
            ambe_frames.clear()

        for word in prebuffer_words:
            send_word(word)

        while True:
            item = encoded_queue.get()
            if item is pipeline_end:
                break
            send_word(item)

        feeder_thread.join(timeout=2.0)
        encoder_thread.join(timeout=2.0)
        if pipeline_error:
            raise pipeline_error[0]

        timing_mark("TX_LETZTER_AMBE_FRAME_CODIERT", f"Restframes={len(ambe_frames)}")
        timing_mark(
            "TX_ENCODER_PUFFER_STATISTIK",
            f"PCMFrames={pcm_frames_produced};PCMQueueMax={encoder_queue_max};"
            f"AMBEQueueMax={encoded_queue_max};FeederFertig={int(feeder_done.is_set())};"
            f"EncoderFertig={int(encoder_done.is_set())}",
        )

        if ambe_debug_path is not None and loopback_samples:
            loopback_path = Path(ambe_debug_path).parent / "04_codec_loopback_8k.wav"
            pcm_loop = array.array("h", loopback_samples)
            import sys
            if sys.byteorder != "little":
                pcm_loop.byteswap()
            write_pcm16_mono(loopback_path, 8000, pcm_loop.tobytes())
            timing_mark(
                "CODEC_LOOPBACK_WAV",
                f"Pfad={loopback_path};Samples={len(loopback_samples)};"
                f"KorrigierteBits={loopback_corrected_errors};"
                f"DecodeAusnahmen={loopback_decode_exceptions};Frames={loopback_frames}",
            )

        # Letzten unvollständigen 60-ms-Burst mit MD380-Stille auffüllen.
        while ambe_frames:
            encode_started = monotonic()
            pad_word = encoder.encode_2450x1150((0,) * PCM_FRAME_SAMPLES)
            encoder_times_ms.append((monotonic() - encode_started) * 1000.0)
            send_word(pad_word)

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
        timing_mark(
            "TX_STREAM_ENDE",
            f"StreamID={stream_id:08X};Sequence={sequence};Src={source_id};"
            f"Dst={destination_id};TS={timeslot};CallType={call_type};VoiceBursts={voice}",
        )
        terminator = _packet(sequence=sequence, source_id=source_id, destination_id=destination_id,
                             repeater_id=source_id, timeslot=timeslot, call_type=call_type,
                             frame_class=DmrdFrameClass.DATA_SYNC, stream_id=stream_id,
                             payload=_encode_full_lc_burst(lc, 0x02),
                             data_type=DmrdDataType.TERMINATOR_WITH_LC.value)
        send_packet(terminator)
        timing_mark("TX_TERMINATOR_GESENDET")
        timing_mark('TX_LETZTER_FRAME_GESENDET')
        if tx_complete_callback is not None:
            try:
                tx_complete_callback()
            except Exception as error:
                timing_mark("TX_ENDE_CALLBACK_FEHLER", str(error))
        tx_elapsed = monotonic() - tx_start

        if wait_for_parrot_echo:
            # Vor jedem Echo wird der RX-Streamzustand deterministisch geleert.
            # Insbesondere der erste Parrot-Test nach Programmstart darf keine
            # implizite Initialisierung durch eingehende Pakete benötigen.
            timing_mark("PARROT_RX_RESET_START")
            if decoder is not None:
                decoder.close()
            decoder = decoder_factory()
            jitter.reset()
            pending_rx_frames.clear()
            echo_stream_id = None
            timing_mark("PARROT_RX_BEREIT")
            # Das Echo-Fenster muss sowohl die BrandMeister-Anlaufzeit als auch
            # die vollständig gesendete Sprachdauer umfassen. Der frühere feste
            # 15-s-Wert kappte eine 15-s-Aufnahme nach rund 11,7 s Wiedergabe,
            # weil bereits etwa 3,3 s bis zum ersten Echo-Paket verstrichen waren.
            echo_wait_seconds = min(
                PARROT_TRANSMIT_CAP_SECONDS + 15.0,
                max(PARROT_ECHO_CAP_SECONDS, tx_elapsed + 10.0),
            )
            timing_mark("PARROT_ECHO_WARTE_START")
            timing_mark("PARROT_ECHO_FENSTER", f"Fenster={echo_wait_seconds:.3f}s;TX={tx_elapsed:.3f}s")
            echo_start = monotonic()
            first_echo_packet_marked = False
            while monotonic() - echo_start < echo_wait_seconds:
                remaining = echo_wait_seconds - (monotonic() - echo_start)
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
                except (TypeError, ValueError) as exc:
                    rx_trace_parse_errors += 1
                    if rx_trace_packets < rx_trace_limit:
                        timing_mark("RX_TRACE_PARSE_FEHLER", f"Index={rx_trace_packets + 1};Fehler={type(exc).__name__}")
                    rx_trace_packets += 1
                    continue
                rx_trace_packets += 1
                frame_name = getattr(packet.frame_class, "name", str(packet.frame_class))
                call_name = getattr(packet.call_type, "name", str(packet.call_type))
                if rx_trace_packets <= rx_trace_limit:
                    timing_mark(
                        "RX_TRACE_DMRD",
                        f"Index={rx_trace_packets};Seq={packet.sequence};Stream={packet.stream_id:08X};"
                        f"Src={packet.source_id};Dst={packet.destination_id};TS={packet.timeslot};"
                        f"Call={call_name};Frame={frame_name};LC={int(packet.is_voice_lc_header)};"
                        f"Term={int(packet.is_terminator_with_lc)}"
                    )
                reject_reasons = []
                if packet.call_type is not DmrdCallType.PRIVATE:
                    reject_reasons.append("Rufart")
                if packet.timeslot != 2:
                    reject_reasons.append("Timeslot")
                if 9990 not in (packet.source_id, packet.destination_id):
                    reject_reasons.append("Ziel")
                if reject_reasons:
                    rx_trace_filter_rejects += 1
                    if rx_trace_packets <= rx_trace_limit:
                        timing_mark("RX_TRACE_VERWORFEN", f"Index={rx_trace_packets};Grund={'+'.join(reject_reasons)}")
                    continue
                if packet.is_voice_lc_header:
                    # Jeder neue Stream beginnt mit einem frischen Decoder- und
                    # Jitterzustand. Das gilt auch für den allerersten Stream.
                    echo_stream_id = packet.stream_id
                    decoder.close()
                    decoder = decoder_factory()
                    jitter.reset(first_voice_sequence=(packet.sequence + 1) & 0xFF)
                    timing_mark("PARROT_STREAM_INITIALISIERT", f"Stream={packet.stream_id:08X};Header=1")
                    continue
                if packet.is_terminator_with_lc:
                    for frame in jitter.flush().frames:
                        play_rx_frame(frame)
                    echo_received = echo_voice > 0
                    timing_mark("PARROT_TERMINATOR_EMPFANGEN", f"VoiceBursts={echo_voice}")
                    break
                if packet.frame_class not in (DmrdFrameClass.VOICE, DmrdFrameClass.VOICE_SYNC):
                    rx_trace_non_voice += 1
                    if rx_trace_packets <= rx_trace_limit:
                        timing_mark("RX_TRACE_KEIN_VOICE", f"Index={rx_trace_packets};Frame={frame_name}")
                    continue
                rx_trace_voice_packets += 1
                # Manche Gegenstellen liefern beim Streamstart keinen verwertbaren
                # LC-Header. Das erste gültige Voice-Paket muss deshalb ebenfalls
                # einen neuen Stream deterministisch eröffnen können.
                if echo_stream_id != packet.stream_id:
                    echo_stream_id = packet.stream_id
                    decoder.close()
                    decoder = decoder_factory()
                    jitter.reset(first_voice_sequence=packet.sequence)
                    timing_mark("PARROT_STREAM_INITIALISIERT", f"Stream={packet.stream_id:08X};Header=0")
                echo_voice += 1
                decoded = []
                try:
                    words = tuple(extract_ambe_codewords(packet))
                    for word in words:
                        frame = decoder.decode(word)
                        decoded.extend(frame.samples)
                        decoded_words += 1
                        rx_trace_decoded_frames += 1
                        rx_trace_pcm_samples += len(frame.samples)
                except Exception as exc:
                    decode_errors += 1
                    if rx_trace_packets <= rx_trace_limit:
                        timing_mark("RX_TRACE_DECODE_FEHLER", f"Index={rx_trace_packets};Fehler={type(exc).__name__}:{exc}")
                    continue
                released = jitter.push(packet.sequence, tuple(decoded)).frames
                if rx_trace_packets <= rx_trace_limit:
                    timing_mark(
                        "RX_TRACE_DECODE_OK",
                        f"Index={rx_trace_packets};Codewords={len(words)};PCM={len(decoded)};JitterFreigabe={len(released)}"
                    )
                for frame in released:
                    play_rx_frame(frame)
            flush_rx_frames()
            timed_out = not echo_received
            timing_mark(
                "RX_TRACE_SUMME",
                f"DMRD={rx_trace_packets};ParseFehler={rx_trace_parse_errors};FilterVerworfen={rx_trace_filter_rejects};"
                f"KeinVoice={rx_trace_non_voice};VoicePakete={rx_trace_voice_packets};"
                f"DecodeFrames={rx_trace_decoded_frames};PCM={rx_trace_pcm_samples};"
                f"EchoVoice={echo_voice};DecodeFehler={decode_errors}"
            )
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
                write_pcm16_mono(rx_debug_path, 8000, pcm.tobytes())
                timing_mark("RX_AUDIO_DEBUG_WAV", f"ParrotNachAMBE8k={rx_debug_path};Samples={len(rx_debug_samples)}")
        return VoiceTransmitResult(authenticated, sent, voice, tx_elapsed, False,
                                   echo_received, echo_voice, timed_out,
                                   decoded_words, output_samples, decode_errors)
    finally:
        timer_resolution.__exit__(None, None, None)
        if decoder is not None:
            decoder.close()
        if not preserve_client:
            client.close()
            timing_mark('TX_VERBINDUNG_GESCHLOSSEN')
        else:
            timing_mark('TX_SESSION_OFFEN_GEHALTEN', 'RX übernimmt denselben BrandMeister-Socket')
        if output is not None:
            output.close()
        if loopback_decoder is not None:
            loopback_decoder.close()
        if rx_debug_dir is not None and not defer_debug_report:
            try:
                schedule_session_report(Path(rx_debug_dir), extra={
                    "codec_loopback_frames": loopback_frames,
                    "codec_loopback_corrected_errors": loopback_corrected_errors,
                    "codec_loopback_decode_exceptions": loopback_decode_exceptions,
                    "codec_loopback_samples": len(loopback_samples),
                    "echo_received": echo_received,
                    "decode_errors": decode_errors,
                })
            finally:
                timing_detach_session()
