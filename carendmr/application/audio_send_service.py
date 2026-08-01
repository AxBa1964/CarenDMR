"""Lokaler Audio-Sendepfad ohne Netzwerk- oder DMR-Sendefunktion."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from carendmr.audio import AudioDevice, AudioDirection, AudioManager, SoundDeviceBackend


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
    MIN_GAIN_PERCENT = 25
    MAX_GAIN_PERCENT = 200
    MAX_OUTPUT_VOLUME_PERCENT = 400

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

    def save_settings(self) -> None:
        self._settings_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "microphone_gain_percent": self._gain_percent,
            "output_volume_percent": self._output_volume_percent,
            "output_muted": self._user_muted,
            "agc_enabled": self._agc_enabled,
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
