"""Lokaler Audio-Sendepfad ohne Netzwerk- oder DMR-Sendefunktion."""

from __future__ import annotations

import json
import os
import queue
import time
import wave
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from threading import Event, Thread
from typing import Callable, Iterator

from carendmr.diagnostics.tx_rx_timing import mark as timing_mark

from carendmr.audio import (
    AudioDevice, AudioDirection, AudioManager, SoundDeviceBackend,
    OptimizerDiagnostics, optimize_transmit_pcm,
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


class LivePcmCapture:
    _END = object()
    def __init__(self, service: "AudioSendService", stop_event: Event, *, max_duration_seconds: float, level_callback=None) -> None:
        self.service=service; self.stop_event=stop_event; self.max_duration_seconds=float(max_duration_seconds); self.level_callback=level_callback
        self.queue: queue.Queue[object]=queue.Queue(); self.sample_count=0; self.error: Exception|None=None
        self.queue_max_chunks=0; self.queue_puts=0; self.queue_gets=0; self.queue_empty_waits=0
        self._raw_pcm_16k: list[int] = []
        self._ambe_pcm_8k: list[int] = []
        self.debug_raw_path: Path | None = None
        self.debug_ambe_path: Path | None = None
        self._resampler = _SpeechBandDecimator16kTo8k()
        self.thread=Thread(target=self._run, name="CarenDMR-Live-Audio", daemon=True)
    def start(self)->None: self.thread.start()
    def _run(self)->None:
        import numpy as np
        service=self.service
        try:
            if service._selected_input is None: service.microphones()
            if service._selected_input is None: raise RuntimeError("Es wurde kein Mikrofon gefunden.")
            factor=service._gain_percent/100.0
            def report(level: float)->None:
                if self.level_callback is not None: self.level_callback(max(0.0,min(100.0,float(level)*factor)))
            def on_block(block)->None:
                mono=np.asarray(block,dtype=np.float32).reshape(-1)
                if not mono.size: return
                mono=np.clip(mono*factor,-1.0,1.0)
                raw_pcm=np.clip(np.rint(mono*32767.0),-32768,32767).astype(np.int16)
                self._raw_pcm_16k.extend(int(v) for v in raw_pcm)
                down=self._resampler.process(mono)
                pcm=np.clip(np.rint(down*32767.0),-32768,32767).astype(np.int16)
                chunk=tuple(int(v) for v in pcm)
                self._ambe_pcm_8k.extend(chunk)
                self.sample_count += len(chunk); self.queue.put(chunk)
                self.queue_puts += 1; self.queue_max_chunks=max(self.queue_max_chunks,self.queue.qsize())
            service._mute_receive()
            if not hasattr(service.backend,"stream_input_blocks_until"): raise RuntimeError("Das Audio-Backend unterstützt kein Live-TX.")
            service.backend.stream_input_blocks_until(input_index=service._selected_input.index, stop_event=self.stop_event, max_duration_seconds=self.max_duration_seconds, sample_rate=service.SAMPLE_RATE, channels=service.CHANNELS, block_callback=on_block, level_callback=report)
        except Exception as error: self.error=error
        finally:
            timing_mark("TX_LETZTER_AUDIOBLOCK_GELESEN", f"Samples={self.sample_count}")
            if service.audio_debug_wav_enabled:
                try:
                    self._write_debug_wavs()
                except Exception as error:
                    timing_mark("TX_AUDIO_DEBUG_FEHLER", str(error))
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
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm.tobytes())

    def _write_debug_wavs(self) -> None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        debug_dir = self.service.project_root / "logs" / "audio_debug"
        self.debug_raw_path = debug_dir / f"tx_{stamp}_01_roh_16k.wav"
        self.debug_ambe_path = debug_dir / f"tx_{stamp}_02_vor_ambe_8k.wav"
        self._write_mono_pcm16_wav(self.debug_raw_path, 16000, self._raw_pcm_16k)
        self._write_mono_pcm16_wav(self.debug_ambe_path, 8000, self._ambe_pcm_8k)
        timing_mark("TX_AUDIO_DEBUG_WAV", f"Roh16k={self.debug_raw_path};VorAMBE8k={self.debug_ambe_path}")

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
    MAX_TX_SAFETY_LIMIT_SECONDS = 180

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
        self._tx_safety_limit_seconds = self._validate_tx_safety_limit(
            settings.get("tx_safety_limit_seconds", 60)
        )
        self._audio_debug_wav_enabled = bool(settings.get("audio_debug_wav_enabled", False))

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

    def set_audio_debug_wav_enabled(self, value: object) -> bool:
        self._audio_debug_wav_enabled = bool(value)
        return self._audio_debug_wav_enabled

    def save_settings(self) -> None:
        self._settings_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "microphone_gain_percent": self._gain_percent,
            "output_volume_percent": self._output_volume_percent,
            "output_muted": self._user_muted,
            "agc_enabled": self._agc_enabled,
            "tx_safety_limit_seconds": self._tx_safety_limit_seconds,
            "audio_debug_wav_enabled": self._audio_debug_wav_enabled,
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
        capture=LivePcmCapture(self, stop_event, max_duration_seconds=max_duration_seconds, level_callback=level_callback)
        capture.start(); return capture

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
