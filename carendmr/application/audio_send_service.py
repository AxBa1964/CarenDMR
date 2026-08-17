"""Lokaler Audio-Sendepfad ohne Netzwerk- oder DMR-Sendefunktion."""

from __future__ import annotations

import json
import os
import queue
import time
from collections import deque
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path

from carendmr.diagnostics.audio_lab import build_level_path_report
from threading import Event, Thread
from typing import Callable, Iterator

from carendmr.diagnostics.tx_rx_timing import mark as timing_mark, attach_session as timing_attach_session
from carendmr.diagnostics.wav_io import write_pcm16_mono

from carendmr.audio import (
    AudioDevice, AudioDirection, AudioManager, SoundDeviceBackend,
    OptimizerDiagnostics, StreamingTxSpeechProcessor, optimize_transmit_pcm,
    TxAudioTunerSettings, StreamingTxAudioTuner, tuner_preset, BufferedPcmOutput,
)


class _SpeechBandDecimator16kTo8k:
    """Kontinuierlicher FIR-Tiefpass mit anschließender Halbierung auf 8 kHz.

    Der Filter begrenzt das Signal vor der Dezimation auf das nutzbare
    Sprachband. Dadurch werden Frequenzen oberhalb der neuen Nyquist-Grenze
    nicht als hörbare Aliasanteile in den AMBE-Eingang zurückgefaltet.
    """

    _TAPS = 63
    _CUTOFF_HZ = 3400.0
    _INPUT_RATE = 16000.0

    def __init__(self) -> None:
        import numpy as np
        n = np.arange(self._TAPS, dtype=np.float64) - (self._TAPS - 1) / 2.0
        normalized = self._CUTOFF_HZ / self._INPUT_RATE
        coefficients = 2.0 * normalized * np.sinc(2.0 * normalized * n)
        coefficients *= np.hamming(self._TAPS)
        coefficients /= np.sum(coefficients)
        self._coefficients = coefficients.astype(np.float32)
        self._history = np.zeros(self._TAPS - 1, dtype=np.float32)

    def process(self, samples):
        import numpy as np
        mono = np.asarray(samples, dtype=np.float32).reshape(-1)
        if not mono.size:
            return np.empty(0, dtype=np.float32)
        combined = np.concatenate((self._history, mono))
        filtered = np.convolve(combined, self._coefficients, mode="valid")
        self._history = combined[-(self._TAPS - 1):].copy()
        return filtered[::2].astype(np.float32, copy=False)


class _AudioTestPreRoll:
    """Kurzzeitiger Mikrofon-Ringpuffer für den geführten Audio-Test."""

    def __init__(self, service: "AudioSendService", seconds: float = 2.0) -> None:
        self.service = service
        self.seconds = float(seconds)
        self.stop_event = Event()
        self.samples = deque(maxlen=max(1, int(service.SAMPLE_RATE * self.seconds)))
        self.error: Exception | None = None
        self.thread = Thread(target=self._run, name="CarenDMR-AudioTest-Vorlauf", daemon=True)

    def start(self) -> None:
        self.thread.start()

    def _run(self) -> None:
        try:
            if self.service._selected_input is None:
                self.service.microphones()
            if self.service._selected_input is None:
                raise RuntimeError("Es wurde kein Mikrofon gefunden.")
            def on_block(block) -> None:
                import numpy as np
                mono = np.asarray(block, dtype=np.float32).reshape(-1)
                if not mono.size:
                    return
                pcm = np.clip(np.rint(np.clip(mono, -1.0, 1.0) * 32767.0), -32768, 32767).astype(np.int16)
                self.samples.extend(int(v) for v in pcm)
            self.service.backend.stream_input_blocks_until(
                input_index=self.service._selected_input.index,
                stop_event=self.stop_event,
                max_duration_seconds=3600.0,
                sample_rate=self.service.SAMPLE_RATE,
                channels=self.service.CHANNELS,
                block_callback=on_block,
                level_callback=None,
            )
        except Exception as exc:
            self.error = exc

    def stop(self) -> tuple[int, ...]:
        self.stop_event.set()
        self.thread.join(timeout=2.0)
        return tuple(self.samples)


class LivePcmCapture:
    _END = object()
    def __init__(self, service: "AudioSendService", stop_event: Event, *, max_duration_seconds: float, level_callback=None, pre_roll_samples: tuple[int, ...] = (), one_shot_audio_test: bool = False, session_dir: Path | None = None) -> None:
        self.service=service; self.stop_event=stop_event; self.max_duration_seconds=float(max_duration_seconds); self.level_callback=level_callback
        self._one_shot_audio_test = bool(one_shot_audio_test)
        self.queue: queue.Queue[object]=queue.Queue(); self.sample_count=0; self.error: Exception|None=None
        self.queue_max_chunks=0; self.queue_puts=0; self.queue_gets=0; self.queue_empty_waits=0
        self._pre_roll_pcm_16k: list[int] = list(pre_roll_samples)
        self._input_pcm_16k: list[int] = []
        self._gain_pcm_16k: list[int] = []
        self._processed_pcm_16k: list[int] = []
        self._ambe_pcm_8k: list[int] = []
        self._collect_debug = bool(service.audio_debug_wav_enabled or self._one_shot_audio_test)
        self.debug_pre_roll_path: Path | None = None
        self.debug_raw_path: Path | None = None
        self.debug_gain_path: Path | None = None
        self.debug_ambe_path: Path | None = None
        self.audio_lab_dir: Path | None = None
        self.ambe_frames_path: Path | None = None
        if service.audio_debug_wav_enabled or self._one_shot_audio_test:
            if self._one_shot_audio_test:
                if session_dir is None:
                    raise RuntimeError("Für den geführten Audio-Test fehlt der Sitzungsordner.")
                self.audio_lab_dir = Path(session_dir)
            else:
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                self.audio_lab_dir = service.project_root / "logs" / "audio_lab" / f"TX_{stamp}"
            self.audio_lab_dir.mkdir(parents=True, exist_ok=True)
            if self._one_shot_audio_test:
                timing_attach_session(self.audio_lab_dir)
            self.ambe_frames_path = self.audio_lab_dir / "04_ambe_frames.bin"
        self._speech_processor = StreamingTxSpeechProcessor(sample_rate=service.SAMPLE_RATE, enabled=service.tx_speech_processing_enabled)
        self._audio_tuner = StreamingTxAudioTuner(service.tx_audio_tuner_settings, sample_rate=service.SAMPLE_RATE)
        self._resampler = _SpeechBandDecimator16kTo8k()
        if self._one_shot_audio_test:
            self._write_test_metadata()
        self.thread=Thread(target=self._run, name="CarenDMR-Live-Audio", daemon=True)
    def start(self)->None: self.thread.start()

    def _write_test_metadata(self) -> None:
        if self.audio_lab_dir is None:
            return
        from carendmr.version import get_version
        selected = self.service._selected_input
        native_rate = int(self.service.SAMPLE_RATE)
        if selected is not None and hasattr(self.service.backend, "resolve_input_sample_rate"):
            try:
                native_rate = int(self.service.backend.resolve_input_sample_rate(
                    selected.index, self.service.SAMPLE_RATE, self.service.CHANNELS
                ))
            except Exception:
                native_rate = int(self.service.SAMPLE_RATE)
        payload = {
            "version": 2,
            "created_at": datetime.now().astimezone().isoformat(),
            "carendmr_version": get_version(),
            "microphone_gain_percent": int(self.service.gain_percent),
            "microphone_gain_factor": round(float(self.service.gain_percent) / 100.0, 6),
            "microphone_gain_db": (
                -120.0 if self.service.gain_percent <= 0
                else round(20.0 * __import__("math").log10(float(self.service.gain_percent) / 100.0), 3)
            ),
            "agc_enabled": bool(self.service.agc_enabled),
            "speech_processing_enabled": bool(self.service.tx_speech_processing_enabled),
            "sample_rate_input_hz": int(self.service.SAMPLE_RATE),
            "sample_rate_device_native_hz": native_rate,
            "resampling_active": native_rate != int(self.service.SAMPLE_RATE),
            "audio_engine": "Audio Engine V2",
            "sample_rate_ambe_hz": 8000,
            "channels": int(self.service.CHANNELS),
            "microphone": {
                "index": getattr(selected, "index", None),
                "name": getattr(selected, "name", None),
                "host_api": getattr(selected, "host_api", None),
            },
            "tx_audio_tuner": self.service.tx_audio_tuner_settings.to_dict(),
        }
        target = self.audio_lab_dir / "test_metadata.json"
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _run(self)->None:
        import numpy as np
        service=self.service
        try:
            if service._selected_input is None: service.microphones()
            if service._selected_input is None: raise RuntimeError("Es wurde kein Mikrofon gefunden.")
            factor=service._gain_percent/100.0
            def report(level: float)->None:
                if self.level_callback is not None: self.level_callback(max(0.0,min(100.0,float(level)*factor)))
            probe_blocks: list[np.ndarray] = []
            probe_samples = 0
            probe_limit = int(service.SAMPLE_RATE * 1.5)
            # Der Audio Coach ist nur Beobachter. Auch beim geführten Test
            # beginnt die TX-Kette exakt wie bei einem normalen PTT.
            signal_released = True

            def process_mono(mono: np.ndarray) -> None:
                input_pcm=np.clip(np.rint(np.clip(mono,-1.0,1.0)*32767.0),-32768,32767).astype(np.int16)
                if self._collect_debug:
                    self._input_pcm_16k.extend(int(v) for v in input_pcm)
                mono=np.clip(mono*factor,-1.0,1.0)
                gain_pcm=np.clip(np.rint(mono*32767.0),-32768,32767).astype(np.int16)
                if self._collect_debug:
                    self._gain_pcm_16k.extend(int(v) for v in gain_pcm)
                processed = self._speech_processor.process(mono)
                processed = self._audio_tuner.process(processed)
                if self._collect_debug:
                    processed_pcm=np.clip(np.rint(processed*32767.0),-32768,32767).astype(np.int16)
                    self._processed_pcm_16k.extend(int(v) for v in processed_pcm)
                down=self._resampler.process(processed)
                pcm=np.clip(np.rint(down*32767.0),-32768,32767).astype(np.int16)
                chunk=tuple(int(v) for v in pcm)
                if self._collect_debug:
                    self._ambe_pcm_8k.extend(chunk)
                self.sample_count += len(chunk); self.queue.put(chunk)
                self.queue_puts += 1; self.queue_max_chunks=max(self.queue_max_chunks,self.queue.qsize())

            def on_block(block)->None:
                nonlocal probe_samples, signal_released
                mono=np.asarray(block,dtype=np.float32)
                if mono.ndim > 1:
                    mono=mono[:, 0]
                mono=mono.reshape(-1)
                if not mono.size:
                    return
                if not signal_released:
                    probe_blocks.append(mono.copy())
                    probe_samples += int(mono.size)
                    peak = max(float(np.max(np.abs(part))) for part in probe_blocks)
                    if peak >= 1.0e-4:
                        signal_released = True
                        buffered=np.concatenate(probe_blocks)
                        probe_blocks.clear()
                        process_mono(buffered)
                        return
                    if probe_samples >= probe_limit:
                        info = dict(getattr(service.backend, "last_input_stream_info", {}) or {})
                        callbacks = int(info.get("callbacks", 0))
                        native_samples = int(info.get("native_samples", 0))
                        capture_channels = int(info.get("capture_channels", 0))
                        channel_peaks = [float(value) for value in (info.get("channel_peak") or [])]
                        peak_text = ", ".join(
                            f"CH{index + 1}={value:.6f}" for index, value in enumerate(channel_peaks)
                        ) or "keine Kanalwerte"
                        self.error=RuntimeError(
                            "Mikrofon geöffnet, aber kein Eingangssignal empfangen. Es wurde nichts gesendet. "
                            f"Callbacks={callbacks}; Samples={native_samples}; Kanäle={capture_channels}; {peak_text}."
                        )
                        self.stop_event.set()
                    return
                process_mono(mono)
            service._mute_receive()
            if not hasattr(service.backend,"stream_input_blocks_until"): raise RuntimeError("Das Audio-Backend unterstützt kein Live-TX.")
            native_rate = service.SAMPLE_RATE
            if hasattr(service.backend, "resolve_input_sample_rate"):
                native_rate = int(service.backend.resolve_input_sample_rate(
                    service._selected_input.index, service.SAMPLE_RATE, service.CHANNELS
                ))
            timing_mark(
                "TX_AUDIO_ENGINE_V2",
                f"Gerät={service._selected_input.name};Host={service._selected_input.host_api};Native={native_rate};Ziel={service.SAMPLE_RATE};AMBE=8000",
            )
            service.backend.stream_input_blocks_until(input_index=service._selected_input.index, stop_event=self.stop_event, max_duration_seconds=self.max_duration_seconds, sample_rate=service.SAMPLE_RATE, channels=service.CHANNELS, block_callback=on_block, level_callback=report)
        except Exception as error: self.error=error
        finally:
            if self.audio_lab_dir is not None:
                try:
                    diagnostics = dict(getattr(service.backend, "last_input_stream_info", {}) or {})
                    diagnostics["processed_samples_16k"] = int(self.sample_count * 2)
                    diagnostics["ambe_samples_8k"] = int(self.sample_count)
                    diagnostics["signal_detected"] = bool(self.sample_count > 0)
                    (self.audio_lab_dir / "input_diagnostics.json").write_text(
                        json.dumps(diagnostics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                    )
                    timing_mark("AUDIO_INPUT_DIAGNOSE", json.dumps(diagnostics, ensure_ascii=False))
                except Exception as error:
                    timing_mark("AUDIO_INPUT_DIAGNOSE_FEHLER", str(error))
            timing_mark("TX_LETZTER_AUDIOBLOCK_GELESEN", f"Samples={self.sample_count}")
            if service.audio_debug_wav_enabled or self._one_shot_audio_test:
                try:
                    self._write_debug_wavs()
                except Exception as error:
                    timing_mark("TX_AUDIO_DEBUG_FEHLER", str(error))
            if self._one_shot_audio_test:
                timing_mark("TX_SPRACHAUFBEREITUNG", json.dumps(self._speech_processor.diagnostics(), ensure_ascii=False))
                timing_mark("TX_AUDIO_TUNER", json.dumps(self._audio_tuner.diagnostics(), ensure_ascii=False))
                timing_mark("AUDIO_TEST_TX_ABGESCHLOSSEN", f"Ordner={self.audio_lab_dir}")
            service._unmute_receive(); self.queue.put(self._END)

    @staticmethod
    def _write_mono_pcm16_wav(path: Path, sample_rate: int, samples: list[int]) -> None:
        import array
        path.parent.mkdir(parents=True, exist_ok=True)
        pcm = array.array("h", samples)
        if os.name != "nt" and pcm.itemsize == 2:
            # WAV ist immer little-endian. Auf den unterstützten Plattformen ist
            # dies normalerweise bereits der Fall; die Prüfung hält es portabel.
            import sys
            if sys.byteorder != "little":
                pcm.byteswap()
        write_pcm16_mono(path, sample_rate, pcm.tobytes())

    def _write_debug_wavs(self) -> None:
        if self.audio_lab_dir is None:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            self.audio_lab_dir = self.service.project_root / "logs" / "audio_lab" / f"TX_{stamp}"
            self.audio_lab_dir.mkdir(parents=True, exist_ok=True)
        self.debug_pre_roll_path = self.audio_lab_dir / "00_vor_ptt_mikrofon_16k.wav"
        self.debug_raw_path = self.audio_lab_dir / "01_mikrofon_roh_16k.wav"
        self.debug_gain_path = self.audio_lab_dir / "02_nach_mic_gain_16k.wav"
        self.debug_processed_path = self.audio_lab_dir / "02a_nach_sprachaufbereitung_16k.wav"
        self.debug_ambe_path = self.audio_lab_dir / "03_vor_ambe_8k.wav"
        self.ambe_frames_path = self.audio_lab_dir / "04_ambe_frames.bin"
        if self._pre_roll_pcm_16k:
            self._write_mono_pcm16_wav(self.debug_pre_roll_path, 16000, self._pre_roll_pcm_16k)
        if self._input_pcm_16k:
            self._write_mono_pcm16_wav(self.debug_raw_path, 16000, self._input_pcm_16k)
        if self._gain_pcm_16k:
            self._write_mono_pcm16_wav(self.debug_gain_path, 16000, self._gain_pcm_16k)
        if self._processed_pcm_16k:
            self._write_mono_pcm16_wav(self.debug_processed_path, 16000, self._processed_pcm_16k)
        if self._ambe_pcm_8k:
            self._write_mono_pcm16_wav(self.debug_ambe_path, 8000, self._ambe_pcm_8k)
        timing_mark("TX_AUDIO_LAB_DATEN_GESICHERT", f"Ordner={self.audio_lab_dir}")
        level_path = build_level_path_report(
            self.audio_lab_dir, gain_percent=self.service.gain_percent
        )
        gain_factor = self.service.gain_percent / 100.0
        import math
        gain_db = -120.0 if gain_factor <= 1e-12 else 20.0 * math.log10(gain_factor)
        timing_mark(
            "TX_PEGELPFAD",
            f"MicGain={self.service.gain_percent}%;Faktor={gain_factor:.3f};GainDb={gain_db:.2f};Bericht={level_path}",
        )

    def chunks(self)->Iterator[tuple[int,...]]:
        while True:
            if self.queue.empty() and self.thread.is_alive(): self.queue_empty_waits += 1
            item=self.queue.get()
            if item is self._END:
                timing_mark("TX_AUDIO_QUEUE_LEER")
                break
            self.queue_gets += 1
            yield item
        self.thread.join(timeout=1.0)
        timing_mark("TX_AUDIO_QUEUE_STATISTIK", f"Puts={self.queue_puts};Gets={self.queue_gets};MaxChunks={self.queue_max_chunks};LeerWarten={self.queue_empty_waits}")
        if self.error is not None: raise self.error
    @property
    def duration_seconds(self)->float: return self.sample_count/8000.0
    @property
    def safety_limit_reached(self)->bool: return self.duration_seconds >= self.max_duration_seconds-0.05


@dataclass(frozen=True, slots=True)
class MicrophoneDiagnostics:
    device_name: str
    host_api: str
    sample_rate: int
    channels: int
    captured_samples: int
    peak_percent: float
    gain_percent: int


class AudioSendService:
    """Bereitet Mikrofon-PCM lokal vor; enthält bewusst keinen Encoder und kein TX."""

    SAMPLE_RATE = 16_000
    CHANNELS = 1
    MIN_GAIN_PERCENT = 0
    MAX_GAIN_PERCENT = 100
    MAX_OUTPUT_VOLUME_PERCENT = 400
    MIN_TX_SAFETY_LIMIT_SECONDS = 5
    MAX_TX_SAFETY_LIMIT_SECONDS = 300

    def __init__(
        self, project_root: Path, *, backend=None,
        mute_receive: Callable[[], None] | None = None,
        unmute_receive: Callable[[], None] | None = None,
    ) -> None:
        self.project_root = Path(project_root)
        self.backend = backend or SoundDeviceBackend()
        self.manager = AudioManager(self.backend, self.project_root / "config" / "audio.local.json")
        self._settings_path = self.project_root / "config" / "audio_send.local.json"
        self._recording = None
        self._peak_percent = 0.0
        self._selected_input: AudioDevice | None = None
        self._mute_receive = mute_receive or (lambda: None)
        self._unmute_receive = unmute_receive or (lambda: None)
        settings = self._load_settings()
        self._gain_percent = self._validate_gain(settings.get("microphone_gain_percent", 100))
        self._output_volume_percent = self._validate_output_volume(settings.get("output_volume_percent", 100))
        self._user_muted = bool(settings.get("output_muted", False))
        self._agc_enabled = bool(settings.get("agc_enabled", True))
        self._tx_speech_processing_enabled = bool(settings.get("tx_speech_processing_enabled", True))
        self._tx_audio_tuner_settings = TxAudioTunerSettings.from_dict(settings.get("tx_audio_tuner", {}))
        stored_tx_limit = settings.get("tx_safety_limit_seconds", 300)
        # Der historische 60-Sekunden-Wert war eine frühe Schutzstufe gegen
        # versehentliches Dauersenden. Ab 0.2.1.43 wird genau dieser alte
        # Standard auf fünf Minuten migriert; abweichend konfigurierte Werte
        # bleiben erhalten.
        if int(round(float(stored_tx_limit))) == 60:
            stored_tx_limit = 300
        self._tx_safety_limit_seconds = self._validate_tx_safety_limit(stored_tx_limit)
        self._audio_debug_wav_enabled = bool(settings.get("audio_debug_wav_enabled", False))
        self._audio_test_armed = False
        self._audio_test_pre_roll: _AudioTestPreRoll | None = None
        self._audio_test_session_dir: Path | None = None
        self._audio_test_waiting_for_rx = False
        self._audio_test_rx_samples: list[int] = []
        self._audio_test_expected_rx_samples = 0

    def _load_settings(self) -> dict[str, object]:
        try:
            raw = json.loads(self._settings_path.read_text(encoding="utf-8"))
            return raw if isinstance(raw, dict) else {}
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return {}

    @classmethod
    def _validate_gain(cls, value: object) -> int:
        gain = int(round(float(value)))
        if not cls.MIN_GAIN_PERCENT <= gain <= cls.MAX_GAIN_PERCENT:
            raise ValueError(f"Die Mikrofonverstärkung muss zwischen {cls.MIN_GAIN_PERCENT} und {cls.MAX_GAIN_PERCENT} Prozent liegen.")
        return gain

    @classmethod
    def _validate_output_volume(cls, value: object) -> int:
        volume = int(round(float(value)))
        if not 0 <= volume <= cls.MAX_OUTPUT_VOLUME_PERCENT:
            raise ValueError(f"Die Ausgabelautstärke muss zwischen 0 und {cls.MAX_OUTPUT_VOLUME_PERCENT} Prozent liegen.")
        return volume


    @classmethod
    def _validate_tx_safety_limit(cls, value: object) -> int:
        limit = int(round(float(value)))
        if not cls.MIN_TX_SAFETY_LIMIT_SECONDS <= limit <= cls.MAX_TX_SAFETY_LIMIT_SECONDS:
            raise ValueError(
                f"Das TX-Sicherheitslimit muss zwischen "
                f"{cls.MIN_TX_SAFETY_LIMIT_SECONDS} und "
                f"{cls.MAX_TX_SAFETY_LIMIT_SECONDS} Sekunden liegen."
            )
        return limit

    @property
    def gain_percent(self) -> int:
        return self._gain_percent

    @property
    def output_volume_percent(self) -> int:
        return self._output_volume_percent

    @property
    def user_muted(self) -> bool:
        return self._user_muted

    @property
    def agc_enabled(self) -> bool:
        return self._agc_enabled

    @property
    def tx_speech_processing_enabled(self) -> bool:
        return self._tx_speech_processing_enabled

    def set_tx_speech_processing_enabled(self, value: object) -> bool:
        self._tx_speech_processing_enabled = bool(value)
        return self._tx_speech_processing_enabled

    @property
    def tx_audio_tuner_settings(self) -> TxAudioTunerSettings:
        return self._tx_audio_tuner_settings

    def set_tx_audio_tuner_settings(self, value: TxAudioTunerSettings | dict[str, object]) -> TxAudioTunerSettings:
        self._tx_audio_tuner_settings = value.normalized() if isinstance(value, TxAudioTunerSettings) else TxAudioTunerSettings.from_dict(value)
        return self._tx_audio_tuner_settings

    def set_tx_audio_tuner_preset(self, name: str) -> TxAudioTunerSettings:
        self._tx_audio_tuner_settings = tuner_preset(name)
        return self._tx_audio_tuner_settings

    @property
    def tx_safety_limit_seconds(self) -> int:
        return self._tx_safety_limit_seconds

    @property
    def audio_debug_wav_enabled(self) -> bool:
        return self._audio_debug_wav_enabled

    def set_gain_percent(self, value: object) -> int:
        self._gain_percent = self._validate_gain(value)
        return self._gain_percent

    def set_output_volume_percent(self, value: object) -> int:
        self._output_volume_percent = self._validate_output_volume(value)
        return self._output_volume_percent

    def set_user_muted(self, value: object) -> bool:
        self._user_muted = bool(value)
        return self._user_muted

    def set_agc_enabled(self, value: object) -> bool:
        self._agc_enabled = bool(value)
        return self._agc_enabled

    def set_tx_safety_limit_seconds(self, value: object) -> int:
        self._tx_safety_limit_seconds = self._validate_tx_safety_limit(value)
        return self._tx_safety_limit_seconds

    @property
    def audio_test_armed(self) -> bool:
        return self._audio_test_armed

    @property
    def audio_test_session_dir(self) -> Path | None:
        return self._audio_test_session_dir

    def arm_audio_test(self, *, pre_roll_seconds: float = 0.0) -> None:
        """Armiert den Coach ohne das Mikrofon vorab zu öffnen.

        Der Coach muss exakt denselben Live-TX-Audiopfad wie ein normaler PTT
        beobachten. Ein separater Vorlauf-Stream kann WASAPI-/Headset-Zustände
        verändern und wird daher bewusst nicht mehr gestartet.
        """
        if self._audio_test_pre_roll is not None:
            self._audio_test_pre_roll.stop()
            self._audio_test_pre_roll = None
        self._audio_test_armed = True
        self._audio_test_session_dir = None
        self._audio_test_waiting_for_rx = False
        self._audio_test_rx_samples.clear()
        self._audio_test_expected_rx_samples = 0
        timing_mark("AUDIO_TEST_BEREIT", "Passiv; kein separater Mikrofon-Vorlauf")

    def cancel_audio_test(self) -> None:
        pre_roll = self._audio_test_pre_roll
        self._audio_test_pre_roll = None
        if pre_roll is not None:
            pre_roll.stop()
        self._audio_test_armed = False
        self._audio_debug_wav_enabled = False
        self._audio_test_waiting_for_rx = False
        timing_mark("AUDIO_TEST_ABGEBROCHEN")

    def _take_audio_test_pre_roll(self) -> tuple[int, ...]:
        pre_roll = self._audio_test_pre_roll
        self._audio_test_pre_roll = None
        if pre_roll is None:
            return ()
        samples = pre_roll.stop()
        if pre_roll.error is not None:
            timing_mark("AUDIO_TEST_VORLAUF_FEHLER", str(pre_roll.error))
        return samples

    def set_audio_debug_wav_enabled(self, value: object) -> bool:
        self._audio_debug_wav_enabled = bool(value)
        return self._audio_debug_wav_enabled

    def save_settings(self) -> None:
        self._settings_path.parent.mkdir(parents=True, exist_ok=True)
        # Ein geführter Test ist immer flüchtig und darf nach einem Neustart
        # keine allgemeine RX-Daueraufzeichnung aktivieren.
        debug_enabled_to_persist = self._audio_debug_wav_enabled and not (self._audio_test_armed or self._audio_test_waiting_for_rx)
        payload = {
            "microphone_gain_percent": self._gain_percent,
            "output_volume_percent": self._output_volume_percent,
            "output_muted": self._user_muted,
            "agc_enabled": self._agc_enabled,
            "tx_speech_processing_enabled": self._tx_speech_processing_enabled,
            "tx_audio_tuner": self._tx_audio_tuner_settings.to_dict(),
            "tx_safety_limit_seconds": self._tx_safety_limit_seconds,
            "audio_debug_wav_enabled": debug_enabled_to_persist,
        }
        self._settings_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def microphones(self) -> tuple[AudioDevice, ...]:
        self.manager.scan()
        devices = self.manager.list_devices(AudioDirection.INPUT)
        if devices and self._selected_input is None:
            try:
                self._selected_input = self.manager.resolve(AudioDirection.INPUT).device
            except Exception:
                self._selected_input = devices[0]
        return devices

    @property
    def selected_input(self) -> AudioDevice | None:
        return self._selected_input

    @property
    def has_recording(self) -> bool:
        return self._recording is not None

    def select_microphone(self, stable_key: str) -> AudioDevice:
        devices = self.manager.list_devices(AudioDirection.INPUT)
        if not devices:
            devices = self.microphones()
        for device in devices:
            if device.stable_key == stable_key:
                self._selected_input = device
                output = self.manager.resolve(AudioDirection.OUTPUT).device
                self.manager.save_selection(device, output)
                return device
        raise ValueError("Das ausgewählte Mikrofon ist nicht mehr verfügbar.")

    def _apply_gain(self, recording):
        import numpy as np
        factor = self._gain_percent / 100.0
        return np.clip(recording * factor, -1.0, 1.0).astype("float32", copy=False)

    def monitor_microphone_until(
        self, stop_event: Event, *, max_duration_seconds: float = 10.0,
        level_callback: Callable[[float], None] | None = None,
    ) -> Path | None:
        """Misst das Mikrofon lokal ohne DMR- oder Netzwerkübertragung.

        Nur bei aktivierter WAV-Audiodiagnose wird das nach Mic Gain
        verarbeitete 16-kHz-Monosignal zusätzlich gespeichert.
        """
        if not 0 < max_duration_seconds <= 30.0:
            raise ValueError("Die Dauer des Mikrofontests muss zwischen 0 und 30 Sekunden liegen.")
        if self._selected_input is None:
            self.microphones()
        if self._selected_input is None:
            raise RuntimeError("Es wurde kein Mikrofon gefunden.")

        debug_samples: list[int] = []

        def consume(block) -> None:
            if not self._audio_debug_wav_enabled:
                return
            import numpy as np
            mono = np.asarray(block, dtype=np.float32).reshape(-1)
            if not mono.size:
                return
            adjusted = np.clip(mono * (self._gain_percent / 100.0), -1.0, 1.0)
            pcm = np.clip(np.rint(adjusted * 32767.0), -32768, 32767).astype(np.int16)
            debug_samples.extend(int(value) for value in pcm)

        def report(level: float) -> None:
            adjusted = max(0.0, min(100.0, float(level) * (self._gain_percent / 100.0)))
            if level_callback is not None:
                level_callback(adjusted)

        self.backend.stream_input_blocks_until(
            input_index=self._selected_input.index, stop_event=stop_event,
            max_duration_seconds=max_duration_seconds, sample_rate=self.SAMPLE_RATE,
            channels=self.CHANNELS, block_callback=consume, level_callback=report,
        )
        if not self._audio_debug_wav_enabled or not debug_samples:
            return None
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        path = self.project_root / "logs" / "audio_debug" / (
            f"mic_test_{stamp}_gain_{self._gain_percent}.wav"
        )
        LivePcmCapture._write_mono_pcm16_wav(path, self.SAMPLE_RATE, debug_samples)
        timing_mark("MIC_TEST_AUDIO_DEBUG_WAV", str(path))
        return path

    def record_test(self, *, duration_seconds: float = 5.0, level_callback: Callable[[float], None] | None = None) -> MicrophoneDiagnostics:
        if duration_seconds <= 0:
            raise ValueError("Die Aufnahmedauer muss größer als null sein.")
        if self._selected_input is None:
            self.microphones()
        if self._selected_input is None:
            raise RuntimeError("Es wurde kein Mikrofon gefunden.")
        self._peak_percent = 0.0
        factor = self._gain_percent / 100.0

        def report(level: float) -> None:
            level = max(0.0, min(100.0, float(level) * factor))
            self._peak_percent = max(self._peak_percent, level)
            if level_callback is not None:
                level_callback(level)

        self._mute_receive()
        try:
            recording = self.backend.record_input(
                input_index=self._selected_input.index, duration_seconds=duration_seconds,
                sample_rate=self.SAMPLE_RATE, channels=self.CHANNELS, level_callback=report,
            )
            self._recording = self._apply_gain(recording)
        finally:
            self._unmute_receive()
        sample_count = int(getattr(self._recording, "shape", [len(self._recording)])[0])
        return MicrophoneDiagnostics(
            device_name=self._selected_input.name, host_api=self._selected_input.host_api,
            sample_rate=self.SAMPLE_RATE, channels=self.CHANNELS,
            captured_samples=sample_count, peak_percent=self._peak_percent,
            gain_percent=self._gain_percent,
        )

    def capture_transmit_pcm(
        self,
        *,
        duration_seconds: float = 5.0,
        level_callback: Callable[[float], None] | None = None,
    ) -> tuple[int, ...]:
        """Erfasst Sprache lokal und liefert exakt 8-kHz/16-Bit-Mono-PCM.

        Diese Methode enthält bewusst keinerlei Netzwerk- oder DMRD-Funktion.
        """
        if not 0 < duration_seconds <= 15.0:
            raise ValueError("Die Parrot-Aufnahme muss zwischen 0 und 15 Sekunden liegen.")
        if self._selected_input is None:
            self.microphones()
        if self._selected_input is None:
            raise RuntimeError("Es wurde kein Mikrofon gefunden.")

        import numpy as np

        factor = self._gain_percent / 100.0
        expected_16k = int(round(self.SAMPLE_RATE * duration_seconds))

        def report(level: float) -> None:
            adjusted = max(0.0, min(100.0, float(level) * factor))
            if level_callback is not None:
                level_callback(adjusted)

        self._mute_receive()
        try:
            recording = self.backend.record_input(
                input_index=self._selected_input.index,
                duration_seconds=duration_seconds,
                sample_rate=self.SAMPLE_RATE,
                channels=self.CHANNELS,
                level_callback=report,
            )
            mono = np.asarray(recording, dtype=np.float32).reshape(-1)
            if mono.size < expected_16k:
                mono = np.pad(mono, (0, expected_16k - mono.size))
            else:
                mono = mono[:expected_16k]
            mono = np.clip(mono * factor, -1.0, 1.0)
            # 16 kHz -> 8 kHz: jeweils zwei benachbarte Samples mitteln.
            downsampled = mono.reshape(-1, 2).mean(axis=1)
            pcm = np.clip(np.rint(downsampled * 32767.0), -32768, 32767).astype(np.int16)
            return tuple(int(value) for value in pcm)
        finally:
            self._unmute_receive()

    def capture_transmit_pcm_until(
        self,
        stop_event: Event,
        *,
        max_duration_seconds: float = 15.0,
        level_callback: Callable[[float], None] | None = None,
        optimize: bool = True,
    ) -> tuple[tuple[int, ...], float, bool, OptimizerDiagnostics | None]:
        """Nimmt beim Gedrückthalten auf und endet beim Loslassen oder Limit."""
        if not self.MIN_TX_SAFETY_LIMIT_SECONDS <= max_duration_seconds <= self.MAX_TX_SAFETY_LIMIT_SECONDS:
            raise ValueError(
                f"Das TX-Sicherheitslimit muss zwischen {self.MIN_TX_SAFETY_LIMIT_SECONDS} "
                f"und {self.MAX_TX_SAFETY_LIMIT_SECONDS} Sekunden liegen."
            )
        if self._selected_input is None:
            self.microphones()
        if self._selected_input is None:
            raise RuntimeError("Es wurde kein Mikrofon gefunden.")

        import numpy as np

        factor = self._gain_percent / 100.0

        def report(level: float) -> None:
            adjusted = max(0.0, min(100.0, float(level) * factor))
            if level_callback is not None:
                level_callback(adjusted)

        self._mute_receive()
        try:
            if hasattr(self.backend, "record_input_until"):
                recording = self.backend.record_input_until(
                    input_index=self._selected_input.index, stop_event=stop_event,
                    max_duration_seconds=max_duration_seconds, sample_rate=self.SAMPLE_RATE,
                    channels=self.CHANNELS, level_callback=report,
                )
            else:
                recording = self.backend.record_input(
                    input_index=self._selected_input.index, duration_seconds=max_duration_seconds,
                    sample_rate=self.SAMPLE_RATE, channels=self.CHANNELS, level_callback=report,
                )
            mono = np.asarray(recording, dtype=np.float32).reshape(-1)
            if mono.size == 0:
                raise RuntimeError("Die TX-Aufnahme enthält keine Audiodaten.")
            mono = np.clip(mono * factor, -1.0, 1.0)
            if mono.size % 2:
                mono = mono[:-1]
            downsampled = mono.reshape(-1, 2).mean(axis=1)
            pcm_array = np.clip(np.rint(downsampled * 32767.0), -32768, 32767).astype(np.int16)
            pcm = tuple(int(value) for value in pcm_array)
            diagnostics = None
            if optimize:
                pcm, diagnostics = optimize_transmit_pcm(pcm, sample_rate=8000)
            duration = len(pcm) / 8000.0
            hit_limit = duration >= max_duration_seconds - 0.05
            return pcm, duration, hit_limit, diagnostics
        finally:
            self._unmute_receive()

    def start_live_capture(self, stop_event: Event, *, max_duration_seconds: float, level_callback: Callable[[float], None] | None = None) -> LivePcmCapture:
        one_shot = self._audio_test_armed
        pre_roll = self._take_audio_test_pre_roll() if one_shot else ()
        session_dir = None
        if one_shot:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            session_dir = self.project_root / "logs" / "audio_lab" / f"AudioTest_{stamp}"
            session_dir.mkdir(parents=True, exist_ok=True)
            self._audio_test_session_dir = session_dir
        capture=LivePcmCapture(self, stop_event, max_duration_seconds=max_duration_seconds, level_callback=level_callback, pre_roll_samples=pre_roll, one_shot_audio_test=one_shot, session_dir=session_dir)
        capture.start()
        if one_shot:
            self._audio_test_armed = False
            timing_mark("AUDIO_TEST_TX_GESTARTET", f"VorlaufSamples={len(pre_roll)}")
        return capture

    def create_pcm_output(self, **kwargs):
        """Erzeugt RX/Parrot-Ausgabe immer auf dem ausdrücklich gewählten Gerät."""
        if not self.manager.devices:
            self.manager.scan()
        output = self.manager.resolve(AudioDirection.OUTPUT).device
        native_rate = int(round(output.default_sample_rate))
        return BufferedPcmOutput(
            output_device_index=output.index,
            output_sample_rate=native_rate,
            **kwargs,
        )

    def mark_audio_test_waiting_for_rx(self, *, expected_samples: int = 0) -> None:
        """Hält die Coach-Sitzung bis zur vollständigen Parrot-Antwort offen.

        Die Soll-Länge stammt aus der gerade tatsächlich gesendeten TX-Aufnahme.
        Damit können kurze/stale DMR-Terminatoren verworfen werden, ohne einen
        künstlichen festen Warte-Timer zu verwenden.
        """
        if self._audio_test_session_dir is not None:
            self._audio_test_waiting_for_rx = True
            self._audio_test_rx_samples.clear()
            self._audio_test_expected_rx_samples = max(0, int(expected_samples))
            timing_mark(
                "AUDIO_TEST_WARTET_AUF_PARROT",
                f"Ordner={self._audio_test_session_dir};SollSamples={self._audio_test_expected_rx_samples}",
            )

    def observe_audio_test_pcm(
        self, source_id: int, destination_id: int, timeslot: int,
        stream_id: int | None, samples: tuple[int, ...], corrected_errors: int = 0,
    ) -> None:
        if not self._audio_test_waiting_for_rx or self._audio_test_session_dir is None:
            return
        if int(source_id) != 9990 or int(timeslot) != 2:
            return
        self._audio_test_rx_samples.extend(int(value) for value in samples)

    def observe_audio_test_call_activity(self, activity) -> None:
        """Schließt den Coach erst am Terminator der real empfangenen Parrot-Antwort ab."""
        if not self._audio_test_waiting_for_rx or self._audio_test_session_dir is None:
            return
        if bool(getattr(activity, "active", True)):
            return
        if int(getattr(activity, "source_id", 0)) != 9990:
            return
        samples = tuple(self._audio_test_rx_samples)
        if not samples:
            return
        # Parrot gibt dieselbe Aussendung zurück. Ein Terminator nach nur einem
        # kurzen Fragment (z. B. 2880 Samples bei ~158000 erwarteten Samples)
        # ist daher nicht das Ende unseres Coach-Echos. Erst ein Streamende mit
        # mindestens 85 % der real gesendeten Sprachlänge darf den Test beenden.
        expected = int(self._audio_test_expected_rx_samples)
        minimum_complete = int(expected * 0.85) if expected > 0 else 0
        if minimum_complete and len(samples) < minimum_complete:
            timing_mark(
                "AUDIO_TEST_PARROT_TERMINATOR_IGNORIERT",
                f"Samples={len(samples)};Mindestens={minimum_complete};Soll={expected}",
            )
            return
        session_dir = Path(self._audio_test_session_dir)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        path = session_dir / f"rx_{stamp}_parrot_nach_ambe_8k.wav"
        self._write_pcm16_wav(path, 8000, samples)
        timing_mark("AUDIO_TEST_PARROT_GESPEICHERT", f"Pfad={path};Samples={len(samples)}")
        from carendmr.diagnostics.audio_report_worker import schedule_session_report
        schedule_session_report(session_dir, extra={
            "echo_received": True,
            "parrot_source_id": 9990,
            "parrot_samples": len(samples),
        })
        self.finish_audio_test_session()

    @staticmethod
    def _write_pcm16_wav(path: Path, sample_rate: int, samples: tuple[int, ...]) -> None:
        import array
        import sys
        pcm = array.array("h", samples)
        if sys.byteorder != "little":
            pcm.byteswap()
        write_pcm16_mono(path, sample_rate, pcm.tobytes())

    def finish_audio_test_session(self) -> None:
        """Schließt den flüchtigen Testzustand nach TX und Parrot-RX sauber ab."""
        if self._audio_test_session_dir is not None:
            timing_mark("AUDIO_TEST_SITZUNG_ABGESCHLOSSEN", f"Ordner={self._audio_test_session_dir}")
        self._audio_test_armed = False
        self._audio_test_waiting_for_rx = False
        self._audio_test_rx_samples.clear()
        self._audio_test_expected_rx_samples = 0
        self._audio_test_session_dir = None

    def play_test(self) -> None:
        if self._recording is None:
            raise RuntimeError("Es liegt noch keine Testaufnahme vor.")
        output = self.manager.resolve(AudioDirection.OUTPUT).device
        self._mute_receive()
        try:
            self.backend.play_samples(self._recording, output_index=output.index, sample_rate=self.SAMPLE_RATE)
        finally:
            self._unmute_receive()

    def run_loopback(self, *, duration_seconds: float = 4.0) -> None:
        self._mute_receive()
        try:
            self.manager.run_loopback_test(duration_seconds=duration_seconds, sample_rate=self.SAMPLE_RATE)
        finally:
            self._unmute_receive()
