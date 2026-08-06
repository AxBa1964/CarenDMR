"""Dynamischer Gruppenruf-Empfang mit Audio-Decodierung und Wiedergabe."""

from __future__ import annotations
from carendmr.diagnostics.wav_io import write_pcm16_mono

import math
import time
import wave
import array
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Callable

from carendmr.audio.pcm_output import BufferedPcmOutput
from carendmr.network import NetworkReceiveTimeout
from carendmr.diagnostics import diagnostic_print
from carendmr.diagnostics.tx_rx_timing import mark as timing_mark
from carendmr.diagnostics.audio_report_worker import schedule_session_report
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
    connected_callback: Callable[[], None] | None = None,
    progress_interval: float = DEFAULT_PROGRESS_INTERVAL_SECONDS,
    heartbeat_interval: float = DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
    stop_requested: Callable[[], bool] | None = None,
    output_muted: Callable[[], bool] | None = None,
    output_volume: Callable[[], float] | None = None,
    output_agc_enabled: Callable[[], bool] | None = None,
    output_level_callback: Callable[[float], None] | None = None,
    decoded_pcm_callback: Callable[[int, int, int, int | None, tuple[int, ...], int], None] | None = None,
    audio_debug_dir: Path | Callable[[], Path | None] | None = None,
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
    rx_decoded_samples: list[int] = []
    rx_output_samples: list[int] = []
    session_dir: Path | None = None
    def resolve_session_dir() -> Path | None:
        nonlocal session_dir
        if session_dir is not None:
            return session_dir
        if audio_debug_dir is None:
            return None
        candidate = audio_debug_dir() if callable(audio_debug_dir) else Path(audio_debug_dir)
        if candidate is None:
            return None
        candidate = Path(candidate)
        if callable(audio_debug_dir):
            session_dir = candidate
        else:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            session_dir = candidate / f"RX_{stamp}"
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir
    def output_tap(values: tuple[int, ...]) -> None:
        if values and resolve_session_dir() is not None:
            rx_output_samples.extend(int(v) for v in values)
    output = output_factory(
        sample_rate=8000, muted=output_muted, volume=output_volume,
        agc_enabled=output_agc_enabled, level_callback=output_level_callback,
        processed_tap=output_tap,
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
    first_datagram_marked = False
    first_target_dmrd_marked = False
    first_header_marked = False
    first_voice_marked = False
    first_decode_marked = False
    first_pcm_handoff_marked = False

    try:
        output.start()
        audio_started = True
        timing_mark("RX_AUDIO_GEOEFFNET")
        diagnostic_print("[DIAG][AUDIO] Ausgabestream geöffnet: 8000 Hz, mono, int16", flush=True)
        synthetic = _synthetic_samples()
        if output_muted is None or not output_muted():
            output.write(synthetic)
        synthetic_count = len(synthetic)
        # Der Audioausgang ist bereits geöffnet. Login und Zielaktivierung geben
        # ihm anschließend ohnehin rund eine halbe Sekunde Anlaufzeit; eine
        # zusätzliche feste 250-ms-Pause verzögert TX→RX nur unnötig.
        timing_mark("RX_AUDIO_VORLAUF_FERTIG", "ohne zusätzliche Wartezeit")

        decoder = decoder_factory()
        diagnostic_print("[DIAG][DECODER] Nativer MBE-Decoder geöffnet", flush=True)
        diagnostic_print(f"[DIAG][NETZ] Verbinde mit {config.host}:{config.port}", flush=True)
        timing_mark("RX_LOGIN_START")
        client.login()
        timing_mark("RX_LOGIN_FERTIG")
        authenticated = client.state is LoginState.CONNECTED
        if not authenticated or client.transport is None:
            raise RuntimeError("Die Empfangsverbindung ist nicht eindeutig aktiv.")
        diagnostic_print("[DIAG][NETZ] BrandMeister-Anmeldung erfolgreich", flush=True)
        diagnostic_print(
            f"[DIAG][ZIEL] Aktiviere TG {target_talkgroup} auf TS{target_timeslot}",
            flush=True,
        )

        timing_mark("RX_ZIELAKTIVIERUNG_START")
        activate_dynamic_talkgroup(
            client.transport,
            dmr_id=config.dmr_id,
            talkgroup=target_talkgroup,
            timeslot=target_timeslot,
            call_type=target_call_type,
        )
        diagnostic_print("[DIAG][ZIEL] Aktivierungsruf vollständig gesendet", flush=True)
        timing_mark("RX_ZIELAKTIVIERUNG_FERTIG")
        # Nach erfolgreichem Login und Zielaktivierung ist RX technisch bereit.
        # Der bisherige Fortschritts-Callback kam erst deutlich später und ließ
        # die Oberfläche unnötig lange auf „Verbindung wird aufgebaut“ stehen.
        if connected_callback is not None:
            connected_callback()

        # Im Dauerempfang darf recv() nicht mehrere Sekunden blockieren, weil
        # PTT den RX-Thread sonst erst nach Ablauf des Login-Timeouts beendet.
        # 100 ms hält die CPU-Last gering und macht den Abbruch praktisch sofort.
        if hasattr(client.transport, "set_receive_timeout"):
            client.transport.set_receive_timeout(0.1)

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
                    diagnostic_print(
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
                if not first_datagram_marked:
                    timing_mark("RX_ERSTES_UDP_DATAGRAMM", f"{len(datagram)} Byte; Start={datagram[:4]!r}")
                    first_datagram_marked = True
                if is_master_pong(datagram, config.dmr_id):
                    pongs += 1
                    continue
                if not datagram.startswith(b"DMRD"):
                    non_dmrd += 1
                    diagnostic_print(
                        f"[DIAG][RX] Sonstiges UDP-Paket: {len(datagram)} Byte, "
                        f"Start={datagram[:12].hex(' ')}",
                        flush=True,
                    )
                    continue
                try:
                    packet = parse_dmrd_packet(datagram)
                except (TypeError, ValueError) as error:
                    invalid += 1
                    diagnostic_print(
                        f"[DIAG][DMRD] Ungültiges Paket ({len(datagram)} Byte): {error}",
                        flush=True,
                    )
                    continue
                frame_name = (
                    f"VOICE-{packet.voice_frame_number}"
                    if packet.frame_class is DmrdFrameClass.VOICE
                    else packet.frame_class.name
                )
                diagnostic_print(
                    f"[DIAG][DMRD] Seq={packet.sequence:03d} Src={packet.source_id} "
                    f"Dst={packet.destination_id} TS{packet.timeslot} "
                    f"Ruf={packet.call_type.name} Frame={frame_name} "
                    f"Stream={packet.stream_id:08X}",
                    flush=True,
                )
                if packet.destination_id != target_talkgroup:
                    rejected_tg += 1
                    diagnostic_print(
                        f"[DIAG][FILTER] VERWORFEN: TG {packet.destination_id} "
                        f"statt TG {target_talkgroup}",
                        flush=True,
                    )
                    continue
                if packet.timeslot != target_timeslot:
                    rejected_ts += 1
                    diagnostic_print(
                        f"[DIAG][FILTER] VERWORFEN: TS{packet.timeslot} "
                        f"statt TS{target_timeslot}",
                        flush=True,
                    )
                    continue
                expected_call_type = "PRIVATE" if target_call_type == "private" else "GROUP"
                if packet.call_type.name != expected_call_type:
                    rejected_call_type += 1
                    diagnostic_print(f"[DIAG][FILTER] VERWORFEN: Rufart {packet.call_type.name} statt {expected_call_type}", flush=True)
                    continue
                diagnostic_print("[DIAG][FILTER] AKZEPTIERT: TG, Timeslot und Rufart passen", flush=True)
                if not first_target_dmrd_marked:
                    timing_mark(
                        "RX_ERSTER_PASSENDER_DMRD_FRAME",
                        f"Seq={packet.sequence}; Src={packet.source_id}; Dst={packet.destination_id}; "
                        f"TS={packet.timeslot}; Frame={frame_name}; Stream={packet.stream_id:08X}",
                    )
                    first_target_dmrd_marked = True
                if packet.is_voice_lc_header:
                    headers += 1
                    if not first_header_marked:
                        timing_mark(
                            "RX_ERSTER_VOICE_LC_HEADER",
                            f"Seq={packet.sequence}; Src={packet.source_id}; Stream={packet.stream_id:08X}",
                        )
                        first_header_marked = True
                    diagnostic_print("[DIAG][FRAME] Voice-LC-Header erkannt; Decoder wird zurückgesetzt", flush=True)
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
                    diagnostic_print("[DIAG][FRAME] Terminator mit LC erkannt", flush=True)
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
                            if not first_pcm_handoff_marked:
                                timing_mark("RX_ERSTE_PCM_UEBERGABE", f"{len(frame)} Samples an Audiopuffer")
                                first_pcm_handoff_marked = True
                            samples += len(frame)
                            audio_writes += 1
                            audio_samples += len(frame)
                            diagnostic_print(f"[DIAG][AUDIO] {len(frame)} PCM-Samples geschrieben", flush=True)
                    concealed += batch.concealed_bursts
                    jitter.reset()
                    continue
                if packet.frame_class not in (
                    DmrdFrameClass.VOICE,
                    DmrdFrameClass.VOICE_SYNC,
                ):
                    rejected_frame += 1
                    diagnostic_print("[DIAG][FILTER] VERWORFEN: kein Sprachrahmen", flush=True)
                    continue

                if call_activity_callback is not None:
                    call_activity_callback(
                        LiveCallActivity(
                            True, packet.source_id, packet.destination_id,
                            packet.timeslot, packet.stream_id or None,
                        )
                    )
                voice += 1
                if not first_voice_marked:
                    timing_mark(
                        "RX_ERSTER_VOICE_FRAME",
                        f"Seq={packet.sequence}; Voice={packet.voice_frame_number}; "
                        f"Src={packet.source_id}; Stream={packet.stream_id:08X}",
                    )
                    first_voice_marked = True
                decoded: list[int] = []
                try:
                    packet_corrected = 0
                    for word in extract_ambe_codewords(packet):
                        frame = decoder.decode(word)
                        decoded.extend(frame.samples)
                        if frame.samples and resolve_session_dir() is not None:
                            rx_decoded_samples.extend(int(v) for v in frame.samples)
                        codewords += 1
                        corrected += frame.corrected_errors
                        packet_corrected += frame.corrected_errors
                    if decoded_pcm_callback is not None and decoded:
                        decoded_pcm_callback(
                            packet.source_id, packet.destination_id, packet.timeslot,
                            packet.stream_id or None, tuple(decoded), packet_corrected,
                        )
                except Exception as error:
                    decode_errors += 1
                    diagnostic_print(
                        f"[DIAG][DECODER] FEHLER {type(error).__name__}: {error}",
                        flush=True,
                    )
                    continue
                if decoded and not first_decode_marked:
                    timing_mark(
                        "RX_ERSTE_AMBE_DECODIERUNG",
                        f"{codewords} Codewörter gesamt; {len(decoded)} PCM-Samples im Frame",
                    )
                    first_decode_marked = True
                diagnostic_print(
                    f"[DIAG][DECODER] 3 AMBE-Codewörter -> {len(decoded)} PCM-Samples",
                    flush=True,
                )

                batch = jitter.push(packet.sequence, tuple(decoded))
                for frame in batch.frames:
                    if output_muted is None or not output_muted():
                        output.write(frame)
                        if not first_pcm_handoff_marked:
                            timing_mark("RX_ERSTE_PCM_UEBERGABE", f"{len(frame)} Samples an Audiopuffer")
                            first_pcm_handoff_marked = True
                        samples += len(frame)
                        audio_writes += 1
                        audio_samples += len(frame)
                        diagnostic_print(f"[DIAG][AUDIO] {len(frame)} PCM-Samples geschrieben", flush=True)
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
                diagnostic_print(f"[DIAG][AUDIO] {len(frame)} PCM-Samples geschrieben (Restpuffer)", flush=True)
        concealed += batch.concealed_bursts
        stopping = stop_requested is not None and stop_requested()
        if not stopping:
            sleep(0.25)
            timing_mark("RX_ABBAU_NACHLAUF_FERTIG", "feste 250 ms")
        else:
            timing_mark("RX_ABBAU_NACHLAUF_FERTIG", "bei aktivem Stopp übersprungen")
        diagnostic_print(
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
        session_dir = resolve_session_dir() if (rx_decoded_samples or rx_output_samples) else session_dir
        if session_dir is not None and (rx_decoded_samples or rx_output_samples):
            def write_wav(path: Path, values: list[int]) -> None:
                import sys
                pcm=array.array("h", values)
                if sys.byteorder != "little": pcm.byteswap()
                write_pcm16_mono(path, 8000, pcm.tobytes())
            if rx_decoded_samples:
                write_wav(session_dir / "05_nach_ambe_decoder_8k.wav", rx_decoded_samples)
            if rx_output_samples:
                write_wav(session_dir / "06_vor_lautsprecher_8k.wav", rx_output_samples)
            schedule_session_report(session_dir, extra={"talkgroup": target_talkgroup, "timeslot": target_timeslot, "call_type": target_call_type})
            timing_mark("RX_AUDIO_LAB", f"Ordner={session_dir}")
        timing_mark("RX_CLOSE_START")
        client.close()
        output.close()
        timing_mark("RX_CLOSE_FERTIG")
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
