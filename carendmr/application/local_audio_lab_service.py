"""Lokales CarenDMR-Audiolabor ohne BrandMeister-Verbindung.

Das Labor ersetzt ausschließlich DMR-Netztransport und Parrot. Die Audio-
Komponenten sind dieselben wie im produktiven Funkbetrieb:
Mikrofon -> AudioSendService.start_live_capture -> TX-Tuner/Sprachaufbereitung
-> 8-kHz-PCM -> EncoderService.create_transmit_encoder -> AMBE ->
NativeMbeReceiveVocoder -> AudioSendService.create_pcm_output -> Soundkarte.
"""
from __future__ import annotations

import array
import json
import math
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from threading import Event, Lock
from typing import Callable

import numpy as np

from carendmr.audio import AudioDirection
from carendmr.diagnostics.wav_io import write_pcm16_mono
from carendmr.encoder.md380_dynarmic import Md380DynarmicEncoder
from carendmr.vocoder import NativeMbeReceiveVocoder, Md380DynarmicReceiveVocoder


@dataclass(frozen=True, slots=True)
class AudioLabRun:
    run_id: str
    created_at: str
    session_dir: str
    settings: dict[str, object]
    metrics: dict[str, object]
    files: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> "AudioLabRun":
        return cls(
            run_id=str(value.get("run_id", "")),
            created_at=str(value.get("created_at", "")),
            session_dir=str(value.get("session_dir", "")),
            settings=dict(value.get("settings") or {}),
            metrics=dict(value.get("metrics") or {}),
            files=dict(value.get("files") or {}),
        )


def _pcm16_metrics(samples, *, sample_rate: int) -> dict[str, float | int]:
    x = np.asarray(tuple(samples), dtype=np.float64)
    if not x.size:
        return {
            "samples": 0, "rms_dbfs": -120.0, "peak_dbfs": -120.0,
            "crest_db": 0.0, "clipped_samples": 0,
            "noise_floor_estimate_dbfs": -120.0,
            "spectral_centroid_hz": 0.0,
        }
    y = x / 32768.0
    abs_y = np.abs(y)
    rms = float(np.sqrt(np.mean(y * y)))
    peak = float(np.max(abs_y))
    crest = 20.0 * math.log10(max(peak, 1e-9) / max(rms, 1e-9))

    frame = max(1, int(round(sample_rate * 0.020)))
    frame_rms = []
    for start in range(0, len(y), frame):
        block = y[start:start + frame]
        if len(block):
            frame_rms.append(float(np.sqrt(np.mean(block * block))))
    # Robuster Näherungswert: leise 10 % der 20-ms-Blöcke.
    noise = float(np.percentile(frame_rms, 10)) if frame_rms else 0.0

    centered = y - float(np.mean(y))
    if len(centered) >= 32:
        window = np.hanning(len(centered))
        spectrum = np.abs(np.fft.rfft(centered * window))
        freqs = np.fft.rfftfreq(len(centered), 1.0 / sample_rate)
        power = spectrum * spectrum
        total = float(np.sum(power))
        centroid = float(np.sum(freqs * power) / total) if total > 1e-20 else 0.0
    else:
        centroid = 0.0

    return {
        "samples": int(len(x)),
        "rms_dbfs": round(max(-120.0, 20.0 * math.log10(max(rms, 1e-6))), 3),
        "peak_dbfs": round(max(-120.0, 20.0 * math.log10(max(peak, 1e-6))), 3),
        "crest_db": round(crest, 3),
        "clipped_samples": int(np.count_nonzero(abs_y >= 0.99997)),
        "noise_floor_estimate_dbfs": round(
            max(-120.0, 20.0 * math.log10(max(noise, 1e-6))), 3
        ),
        "spectral_centroid_hz": round(centroid, 1),
    }


def _band_percent(samples, sample_rate: int, low: float, high: float) -> float:
    x = np.asarray(tuple(samples), dtype=np.float64) / 32768.0
    if len(x) < 32:
        return 0.0
    x -= float(np.mean(x))
    spectrum = np.fft.rfft(x * np.hanning(len(x)))
    power = np.abs(spectrum) ** 2
    freqs = np.fft.rfftfreq(len(x), 1.0 / sample_rate)
    total_mask = (freqs >= 100.0) & (freqs <= min(3800.0, sample_rate / 2.0))
    band_mask = (freqs >= low) & (freqs < min(high, sample_rate / 2.0))
    total = float(np.sum(power[total_mask]))
    return round(100.0 * float(np.sum(power[band_mask])) / total, 2) if total > 1e-20 else 0.0


def _similarity(reference, result, *, max_lag: int = 400) -> dict[str, float]:
    """Pegelunabhängige Ähnlichkeit plus Residual-SNR nach bestmöglicher Ausrichtung."""
    a = np.asarray(tuple(reference), dtype=np.float64)
    b = np.asarray(tuple(result), dtype=np.float64)
    if not len(a) or not len(b):
        return {"similarity_percent": 0.0, "residual_snr_db": -120.0, "best_lag_samples": 0}

    # AMBE-/Decoderanfang kann wenige Frames versetzt sein. Nur kleine,
    # deterministische Verschiebungen zulassen; kein "Schönrechnen".
    best = (-2.0, 0, None, None)
    for lag in range(-max_lag, max_lag + 1, 20):
        if lag >= 0:
            aa, bb = a[lag:], b[:len(a) - lag]
        else:
            aa, bb = a[:len(a) + lag], b[-lag:]
        n = min(len(aa), len(bb))
        if n < 800:
            continue
        aa, bb = aa[:n], bb[:n]
        aa0 = aa - float(np.mean(aa))
        bb0 = bb - float(np.mean(bb))
        denom = float(np.linalg.norm(aa0) * np.linalg.norm(bb0))
        corr = float(np.dot(aa0, bb0) / denom) if denom > 1e-12 else 0.0
        if corr > best[0]:
            best = (corr, lag, aa0, bb0)
    corr, lag, aa0, bb0 = best
    if aa0 is None or bb0 is None:
        return {"similarity_percent": 0.0, "residual_snr_db": -120.0, "best_lag_samples": 0}

    # Optimaler linearer Pegelfaktor trennt Lautstärke von Codec-Verzerrung.
    denom = float(np.dot(aa0, aa0))
    gain = float(np.dot(aa0, bb0) / denom) if denom > 1e-12 else 0.0
    residual = bb0 - aa0 * gain
    signal_power = float(np.mean((aa0 * gain) ** 2))
    error_power = float(np.mean(residual ** 2))
    snr = 10.0 * math.log10(max(signal_power, 1e-12) / max(error_power, 1e-12))
    return {
        "similarity_percent": round(max(0.0, min(100.0, corr * 100.0)), 2),
        "residual_snr_db": round(max(-120.0, snr), 2),
        "best_lag_samples": int(lag),
    }


class LocalAudioLabService:
    """Ein lokaler, wiederholbarer DMR-Audio-Loopback mit Verlauf."""

    LEAD_IN_SECONDS = 0.240
    FRAME_SAMPLES = 160

    def __init__(self, project_root: Path, audio_service, encoder_service) -> None:
        self.project_root = Path(project_root)
        self.audio_service = audio_service
        self.encoder_service = encoder_service
        self.history_path = self.project_root / "logs" / "audio_lab_local" / "history.json"
        self._lock = Lock()
        self._capture = None
        self._stop_event: Event | None = None
        self._previous_debug = False

    @property
    def is_recording(self) -> bool:
        return self._capture is not None

    def _settings_snapshot(self) -> dict[str, object]:
        mic = self.audio_service.selected_input
        try:
            if not self.audio_service.manager.devices:
                self.audio_service.manager.scan()
            output = self.audio_service.manager.resolve(AudioDirection.OUTPUT).device
        except Exception:
            output = None
        tuner = self.audio_service.tx_audio_tuner_settings
        return {
            "microphone": getattr(mic, "name", ""),
            "microphone_host_api": getattr(mic, "host_api", ""),
            "output_device": getattr(output, "name", ""),
            "microphone_gain_percent": int(self.audio_service.gain_percent),
            "tx_speech_processing_enabled": bool(self.audio_service.tx_speech_processing_enabled),
            "tx_profile": str(tuner.profile),
            "tx_low_db": float(tuner.low_db),
            "tx_mids_db": float(tuner.mids_db),
            "tx_presence_db": float(tuner.presence_db),
            "tx_high_db": float(tuner.high_db),
            "tx_dynamics_percent": int(tuner.dynamics_percent),
            "tx_limiter_percent": int(tuner.limiter_percent),
            "rx_volume_percent": int(self.audio_service.output_volume_percent),
            "rx_agc_enabled": bool(self.audio_service.agc_enabled),
        }

    def start_recording(self, *, max_duration_seconds: float = 30.0) -> None:
        with self._lock:
            if self._capture is not None:
                raise RuntimeError("Das Audiolabor zeichnet bereits auf.")
            if self.audio_service.selected_input is None:
                self.audio_service.microphones()
            if self.audio_service.selected_input is None:
                raise RuntimeError("Es wurde kein Mikrofon gefunden.")
            self._previous_debug = bool(self.audio_service.audio_debug_wav_enabled)
            # Nur Beobachterpuffer aktivieren; die Audioverarbeitung ändert sich nicht.
            self.audio_service.set_audio_debug_wav_enabled(True)
            self._stop_event = Event()
            self._capture = self.audio_service.start_live_capture(
                self._stop_event,
                max_duration_seconds=max_duration_seconds,
            )

    def cancel_recording(self) -> None:
        with self._lock:
            stop = self._stop_event
            capture = self._capture
            self._stop_event = None
            self._capture = None
        if stop is not None:
            stop.set()
        if capture is not None:
            try:
                list(capture.chunks())
            except Exception:
                pass
        self.audio_service.set_audio_debug_wav_enabled(self._previous_debug)

    @staticmethod
    def _write_wav(path: Path, sample_rate: int, samples) -> None:
        pcm = array.array("h", (int(v) for v in samples))
        import sys
        if sys.byteorder != "little":
            pcm.byteswap()
        write_pcm16_mono(path, sample_rate, pcm.tobytes())

    @staticmethod
    def _neutral_16k_to_8k(samples: tuple[int, ...]) -> tuple[int, ...]:
        """Neutraler Referenz-Downsample ohne CarenDMR-Tuner/Sprachprozessor.

        Der Referenzpfad bildet DroidStar nach: 8 kHz, Mono, int16 direkt in
        md380_encode_fec. Da unser Windows-Mikrofonpfad 16 kHz liefert, wird
        ausschließlich bandbegrenztes Resampling auf 8 kHz durchgeführt.
        """
        if not samples:
            return tuple()
        from scipy.signal import resample_poly
        data = np.asarray(samples, dtype=np.float64)
        out = resample_poly(data, 1, 2)
        out = np.clip(np.rint(out), -32768, 32767).astype(np.int16)
        return tuple(int(v) for v in out)

    def _encode_decode_md380(
        self,
        pcm_8k: tuple[int, ...],
        *,
        input_gain_db: float,
        ambe_path: Path,
    ) -> tuple[tuple[int, ...], dict[str, int]]:
        """MD380 encode_fec -> MD380 decode_fec für einen PCM-Referenzpfad."""
        lead = (0,) * int(round(8000 * self.LEAD_IN_SECONDS))
        pcm = lead + tuple(int(v) for v in pcm_8k)
        encoder = Md380DynarmicEncoder(
            self.project_root,
            input_gain_db=input_gain_db,
        )
        decoder = Md380DynarmicReceiveVocoder(self.project_root)
        decoded: list[int] = []
        frames = 0
        decode_errors = 0
        ambe_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with ambe_path.open("wb") as ambe:
                for offset in range(0, len(pcm), self.FRAME_SAMPLES):
                    frame = tuple(pcm[offset:offset + self.FRAME_SAMPLES])
                    if len(frame) < self.FRAME_SAMPLES:
                        frame += (0,) * (self.FRAME_SAMPLES - len(frame))
                    word = encoder.encode_2450x1150(frame)
                    if len(word) != 9:
                        raise RuntimeError("Der MD380-Encoder lieferte keinen 9-Byte-AMBE-Rahmen.")
                    ambe.write(word)
                    try:
                        result = decoder.decode(word)
                    except Exception:
                        decode_errors += 1
                        raise
                    decoded.extend(int(v) for v in result.samples)
                    frames += 1
        finally:
            encoder.close()
            decoder.close()
        return tuple(decoded), {
            "codec_frames": frames,
            "decode_errors": decode_errors,
            "input_gain_db": float(input_gain_db),
        }

    def _codec_loopback_ab(
        self, chunks, *, ambe_path: Path
    ) -> tuple[tuple[int, ...], tuple[int, ...], dict[str, int]]:
        """Gleicher MD380-Encoder/AMBE-Frame, zwei Decoder.

        A = aktueller CarenDMR-RX-Decoder (mbelib)
        B = MD380 md380_decode_fec (DroidStar-Referenz)
        """
        pcm = [0] * int(round(8000 * self.LEAD_IN_SECONDS))
        for chunk in chunks:
            pcm.extend(int(v) for v in chunk)

        encoder = self.encoder_service.create_transmit_encoder()
        if not hasattr(encoder, "decode_2450x1150"):
            raise RuntimeError(
                "Der A/B-Test benötigt die MD380-Dynarmic-Bridge mit "
                "md380_decode_fec."
            )
        decoder_a = NativeMbeReceiveVocoder()
        decoder_b = Md380DynarmicReceiveVocoder(self.project_root)
        decoded_a: list[int] = []
        decoded_b: list[int] = []
        corrected_a = 0
        frames = 0
        decode_errors_a = 0
        decode_errors_b = 0
        ambe_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with ambe_path.open("wb") as ambe:
                for offset in range(0, len(pcm), self.FRAME_SAMPLES):
                    frame = tuple(pcm[offset:offset + self.FRAME_SAMPLES])
                    if len(frame) < self.FRAME_SAMPLES:
                        frame += (0,) * (self.FRAME_SAMPLES - len(frame))
                    word = encoder.encode_2450x1150(frame)
                    if len(word) != 9:
                        raise RuntimeError("Der produktive Encoder lieferte keinen 9-Byte-AMBE-Rahmen.")
                    ambe.write(word)

                    try:
                        result_a = decoder_a.decode(word)
                    except Exception:
                        decode_errors_a += 1
                        raise
                    decoded_a.extend(int(v) for v in result_a.samples)
                    corrected_a += max(0, int(result_a.corrected_errors))

                    try:
                        result_b = decoder_b.decode(word)
                    except Exception:
                        decode_errors_b += 1
                        raise
                    decoded_b.extend(int(v) for v in result_b.samples)
                    frames += 1
        finally:
            close = getattr(encoder, "close", None)
            if callable(close):
                close()
            decoder_a.close()
            decoder_b.close()

        return tuple(decoded_a), tuple(decoded_b), {
            "codec_frames": frames,
            "decoder_a_corrected_errors": corrected_a,
            "decoder_a_decode_errors": decode_errors_a,
            "decoder_b_decode_errors": decode_errors_b,
        }

    def _play_through_productive_rx(
        self, decoded: tuple[int, ...]
    ) -> tuple[tuple[int, ...], int]:
        """Spielt über exakt den produktiven RX-Ausgabepfad.

        Wichtig: BufferedPcmOutput resampelt 8-kHz-RX-PCM bereits in write()
        auf die native Rate des gewählten Ausgabegeräts (z. B. 48 kHz).
        processed_tap sieht deshalb *native-rate* Samples. Der erste Laborstand
        speicherte diese Samples fälschlich als 8-kHz-WAV; dadurch wurde eine
        12-s-Aufnahme etwa sechsmal so lang und klang extrem verlangsamt.
        """
        processed: list[int] = []
        output = self.audio_service.create_pcm_output(
            sample_rate=8000,
            processed_tap=lambda block: processed.extend(int(v) for v in block),
        )
        native_rate = int(getattr(output, "_output_sample_rate", 8000) or 8000)
        self.audio_service._mute_receive()
        try:
            output.start()
            # Genau wie DMR RX: drei 20-ms-Codecframes = 480 Samples je 60 ms.
            for start in range(0, len(decoded), 480):
                output.write(decoded[start:start + 480])
                time.sleep(0.060)
            # Restpuffer sicher ausspielen.
            deadline = time.monotonic() + 1.0
            while time.monotonic() < deadline:
                with output._lock:
                    empty = not output._buffer
                if empty:
                    break
                time.sleep(0.020)
            time.sleep(0.080)
        finally:
            output.close()
            self.audio_service._unmute_receive()
        return tuple(processed), native_rate

    def finish_recording_and_play(self) -> AudioLabRun:
        """Stoppt Aufnahme, codiert/decodiert lokal und spielt Ergebnis einmal vor."""
        with self._lock:
            if self._capture is None or self._stop_event is None:
                raise RuntimeError("Im Audiolabor läuft keine Aufnahme.")
            capture = self._capture
            stop = self._stop_event
            self._capture = None
            self._stop_event = None
            settings = self._settings_snapshot()
        stop.set()
        try:
            chunks = list(capture.chunks())
            if not chunks:
                raise RuntimeError("Die Aufnahme enthält keine Audiodaten.")
            session = Path(capture.audio_lab_dir or (
                self.project_root / "logs" / "audio_lab_local" /
                datetime.now().strftime("AudioLab_%Y%m%d_%H%M%S_%f")
            ))
            session.mkdir(parents=True, exist_ok=True)

            before_ambe = tuple(int(v) for v in capture._ambe_pcm_8k)
            if not before_ambe:
                raise RuntimeError("Der produktive TX-Messpunkt vor AMBE ist leer.")

            # A = heutiger CarenDMR-TX-Pfad bis vor AMBE, inkl. +2 dB MD380-Eingang.
            carendmr_before_ambe = before_ambe
            ambe_a_path = session / "04A_ambe_carendmr.bin"
            decoded_a, stats_a = self._encode_decode_md380(
                carendmr_before_ambe,
                input_gain_db=2.0,
                ambe_path=ambe_a_path,
            )

            # B = DroidStar-Referenz: Mikrofon roh -> nur neutrales 16->8-kHz
            # Resampling -> 0 dB -> MD380 encode_fec -> MD380 decode_fec.
            mic_raw_16k = tuple(int(v) for v in capture._input_pcm_16k)
            droidstar_pcm_8k = self._neutral_16k_to_8k(mic_raw_16k)
            droidstar_input_path = session / "03B_droidstar_referenz_vor_ambe_8k.wav"
            self._write_wav(droidstar_input_path, 8000, droidstar_pcm_8k)
            ambe_b_path = session / "04B_ambe_droidstar_referenz.bin"
            decoded_b, stats_b = self._encode_decode_md380(
                droidstar_pcm_8k,
                input_gain_db=0.0,
                ambe_path=ambe_b_path,
            )

            decoded_a_path = session / "05A_carendmr_md380_8k.wav"
            decoded_b_path = session / "05B_droidstar_referenz_md380_8k.wav"
            self._write_wav(decoded_a_path, 8000, decoded_a)
            self._write_wav(decoded_b_path, 8000, decoded_b)

            processed_a, rx_output_rate_a = self._play_through_productive_rx(decoded_a)
            processed_b, rx_output_rate_b = self._play_through_productive_rx(decoded_b)
            processed_a_path = session / f"06A_carendmr_rx_{rx_output_rate_a}hz.wav"
            processed_b_path = session / f"06B_droidstar_referenz_rx_{rx_output_rate_b}hz.wav"
            self._write_wav(processed_a_path, rx_output_rate_a, processed_a)
            self._write_wav(processed_b_path, rx_output_rate_b, processed_b)

            lead = (0,) * int(round(8000 * self.LEAD_IN_SECONDS))
            reference_a = lead + carendmr_before_ambe
            reference_b = lead + droidstar_pcm_8k

            before_a_metrics = _pcm16_metrics(carendmr_before_ambe, sample_rate=8000)
            before_b_metrics = _pcm16_metrics(droidstar_pcm_8k, sample_rate=8000)
            levels_a = _pcm16_metrics(decoded_a, sample_rate=8000)
            levels_b = _pcm16_metrics(decoded_b, sample_rate=8000)
            rx_a = _pcm16_metrics(processed_a, sample_rate=rx_output_rate_a)
            rx_b = _pcm16_metrics(processed_b, sample_rate=rx_output_rate_b)

            qa = _similarity(reference_a, decoded_a)
            qb = _similarity(reference_b, decoded_b)
            qa.update({
                "codec_rms_change_db": round(levels_a["rms_dbfs"] - before_a_metrics["rms_dbfs"], 3),
                "presence_band_percent": _band_percent(decoded_a, 8000, 1800, 3400),
                "low_band_percent": _band_percent(decoded_a, 8000, 100, 600),
                "crest_change_db": round(levels_a["crest_db"] - before_a_metrics["crest_db"], 3),
            })
            qb.update({
                "codec_rms_change_db": round(levels_b["rms_dbfs"] - before_b_metrics["rms_dbfs"], 3),
                "presence_band_percent": _band_percent(decoded_b, 8000, 1800, 3400),
                "low_band_percent": _band_percent(decoded_b, 8000, 100, 600),
                "crest_change_db": round(levels_b["crest_db"] - before_b_metrics["crest_db"], 3),
            })

            basic = {
                "mic_raw_16k": _pcm16_metrics(mic_raw_16k, sample_rate=16000),
                "after_mic_gain_16k": _pcm16_metrics(capture._gain_pcm_16k, sample_rate=16000),
                "after_tx_processing_16k": _pcm16_metrics(capture._processed_pcm_16k, sample_rate=16000),
                "before_ambe_8k": before_a_metrics,
                "droidstar_reference_before_ambe_8k": before_b_metrics,
                "decoder_a_carendmr_8k": levels_a,
                "decoder_b_droidstar_reference_8k": levels_b,
                "rx_a_carendmr_native": rx_a,
                "rx_b_droidstar_reference_native": rx_b,
                "after_codec_8k": levels_b,
                "rx_before_soundcard_native": rx_b,
            }

            quality = {
                "path_a_carendmr": qa,
                "path_b_droidstar_reference": qb,
                "tx_presence_a_percent": _band_percent(carendmr_before_ambe, 8000, 1800, 3400),
                "tx_presence_b_percent": _band_percent(droidstar_pcm_8k, 8000, 1800, 3400),
                "tx_low_a_percent": _band_percent(carendmr_before_ambe, 8000, 100, 600),
                "tx_low_b_percent": _band_percent(droidstar_pcm_8k, 8000, 100, 600),
                "rx_gain_a_db": round(rx_a["rms_dbfs"] - levels_a["rms_dbfs"], 3),
                "rx_gain_b_db": round(rx_b["rms_dbfs"] - levels_b["rms_dbfs"], 3),
                "codec_rms_change_db": qb["codec_rms_change_db"],
                "rx_gain_db": round(rx_b["rms_dbfs"] - levels_b["rms_dbfs"], 3),
                "similarity_percent": qb["similarity_percent"],
                "residual_snr_db": qb["residual_snr_db"],
                "crest_change_db": qb["crest_change_db"],
            }

            metrics = {
                "levels": basic,
                "quality": quality,
                "codec": {
                    "path_a": stats_a,
                    "path_b": stats_b,
                },
                "rates": {
                    "carendmr_before_ambe_hz": 8000,
                    "droidstar_reference_before_ambe_hz": 8000,
                    "decoder_a_hz": 8000,
                    "decoder_b_hz": 8000,
                    "rx_a_before_soundcard_hz": rx_output_rate_a,
                    "rx_b_before_soundcard_hz": rx_output_rate_b,
                },
                "durations_seconds": {
                    "decoder_a": round(len(decoded_a) / 8000.0, 3),
                    "decoder_b": round(len(decoded_b) / 8000.0, 3),
                    "rx_a": round(len(processed_a) / float(rx_output_rate_a), 3),
                    "rx_b": round(len(processed_b) / float(rx_output_rate_b), 3),
                },
            }

            files = {
                "mic_raw": str(getattr(capture, "debug_raw_path", "") or ""),
                "after_mic_gain": str(getattr(capture, "debug_gain_path", "") or ""),
                "after_tx_processing": str(getattr(capture, "debug_processed_path", "") or ""),
                "before_ambe": str(getattr(capture, "debug_ambe_path", "") or ""),
                "droidstar_reference_before_ambe": str(droidstar_input_path),
                "ambe_a_carendmr": str(ambe_a_path),
                "ambe_b_droidstar_reference": str(ambe_b_path),
                "decoder_a_carendmr": str(decoded_a_path),
                "decoder_b_droidstar_reference": str(decoded_b_path),
                "rx_a_carendmr": str(processed_a_path),
                "rx_b_droidstar_reference": str(processed_b_path),
                "codec_loopback": str(decoded_b_path),
                "rx_output": str(processed_b_path),
            }
            run = AudioLabRun(
                run_id=session.name,
                created_at=datetime.now().astimezone().isoformat(),
                session_dir=str(session),
                settings=settings,
                metrics=metrics,
                files=files,
            )
            (session / "local_audio_lab_result.json").write_text(
                json.dumps(run.to_dict(), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            self._append_history(run)
            return run
        finally:
            self.audio_service.set_audio_debug_wav_enabled(self._previous_debug)

    def _append_history(self, run: AudioLabRun) -> None:
        rows = [r.to_dict() for r in self.load_history(limit=30)]
        rows.append(run.to_dict())
        rows = rows[-30:]
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        self.history_path.write_text(
            json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def load_history(self, *, limit: int = 4) -> list[AudioLabRun]:
        try:
            data = json.loads(self.history_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return []
        if not isinstance(data, list):
            return []
        result = []
        for item in data[-max(1, int(limit)):]:
            if isinstance(item, dict):
                result.append(AudioLabRun.from_dict(item))
        return result

    def _play_saved_wav(self, path: Path) -> None:
        if not path.is_file():
            raise RuntimeError(f"Gespeicherte Labor-WAV fehlt: {path}")
        import wave
        with wave.open(str(path), "rb") as wav:
            if wav.getsampwidth() != 2 or wav.getnchannels() != 1:
                raise RuntimeError("Die gespeicherte Labor-WAV hat ein unerwartetes Format.")
            sample_rate = int(wav.getframerate())
            raw = wav.readframes(wav.getnframes())
        pcm = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
        if not self.audio_service.manager.devices:
            self.audio_service.manager.scan()
        output = self.audio_service.manager.resolve(AudioDirection.OUTPUT).device
        self.audio_service._mute_receive()
        try:
            self.audio_service.backend.play_samples(
                pcm, output_index=output.index, sample_rate=sample_rate
            )
        finally:
            self.audio_service._unmute_receive()

    def play_decoder_a(self, run: AudioLabRun) -> None:
        self._play_saved_wav(Path(str(run.files.get("rx_a_carendmr", ""))))

    def play_decoder_b(self, run: AudioLabRun) -> None:
        self._play_saved_wav(Path(str(run.files.get("rx_b_droidstar_reference", ""))))

    def replay_run(self, run: AudioLabRun) -> None:
        self.play_decoder_b(run)

    def play_original(self, run: AudioLabRun) -> None:
        path = Path(str(run.files.get("mic_raw", "")))
        if not path.is_file():
            raise RuntimeError("Die Mikrofon-Originalaufnahme dieses Durchgangs fehlt.")
        self._play_saved_wav(path)
