"""Auswahl von Mikrofon und Lautsprecher für die Ersteinrichtung (Qt-frei)."""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from carendmr.audio import AudioDirection, AudioManager, SoundDeviceBackend

TEST_TONE_HZ = 1000.0
TEST_TONE_SECONDS = 0.8
TEST_TONE_AMPLITUDE = 0.25
TEST_TONE_RATE = 48000
# Windows-Standardweg (MME „Microsoft Soundmapper“): folgt immer dem in
# Windows eingestellten Gerät; bewährt in der Entwicklungsumgebung.
SOUNDMAPPER_PREFIX = "microsoft soundmapper"
RECOMMENDED_LABEL = "Windows-Standardgerät (empfohlen)"


@dataclass(frozen=True, slots=True)
class AudioChoice:
    key: str
    label: str


class AudioSetupService:
    def __init__(self, project_root: Path, manager: AudioManager | None = None) -> None:
        self.config_path = Path(project_root) / "config" / "audio.local.json"
        self._manager = manager

    @property
    def manager(self) -> AudioManager:
        if self._manager is None:
            self._manager = AudioManager(SoundDeviceBackend(), self.config_path)
        return self._manager

    def needs_setup(self) -> bool:
        return not self.config_path.is_file()

    def scan(self) -> tuple[list[AudioChoice], list[AudioChoice]]:
        manager = self.manager
        manager.scan()
        return (
            self._choices(AudioDirection.INPUT),
            self._choices(AudioDirection.OUTPUT),
        )

    @staticmethod
    def _is_soundmapper(device) -> bool:
        return (
            device.host_api.strip().casefold() == "mme"
            and device.name.strip().casefold().startswith(SOUNDMAPPER_PREFIX)
        )

    def _choices(self, direction: AudioDirection) -> list[AudioChoice]:
        recommended: list[AudioChoice] = []
        others: list[AudioChoice] = []
        for device in self.manager.list_devices(direction):
            if self._is_soundmapper(device):
                recommended.append(AudioChoice(device.stable_key, RECOMMENDED_LABEL))
            else:
                others.append(AudioChoice(device.stable_key, device.display_name(direction)))
        return recommended[:1] + others

    def recommended_keys(self) -> tuple[str | None, str | None]:
        keys: list[str | None] = []
        for direction in (AudioDirection.INPUT, AudioDirection.OUTPUT):
            key = next(
                (d.stable_key for d in self.manager.list_devices(direction) if self._is_soundmapper(d)),
                None,
            )
            keys.append(key)
        return keys[0], keys[1]

    def current_keys(self) -> tuple[str | None, str | None]:
        """Gespeicherte Auswahl; beim ersten Einrichten der empfohlene Weg."""
        if self.needs_setup():
            recommended = self.recommended_keys()
            if recommended[0] and recommended[1]:
                return recommended
        keys: list[str | None] = []
        for direction in (AudioDirection.INPUT, AudioDirection.OUTPUT):
            try:
                keys.append(self.manager.resolve(direction).device.stable_key)
            except Exception:
                keys.append(None)
        return keys[0], keys[1]

    def _device(self, key: str, direction: AudioDirection):
        for device in self.manager.list_devices(direction):
            if device.stable_key == key:
                return device
        raise ValueError("Das ausgewählte Audiogerät ist nicht mehr vorhanden.")

    def save(self, input_key: str, output_key: str) -> None:
        self.manager.save_selection(
            self._device(input_key, AudioDirection.INPUT),
            self._device(output_key, AudioDirection.OUTPUT),
        )

    def play_test_tone(self, output_key: str) -> None:
        """Spielt einen kurzen 1-kHz-Ton auf dem gewählten Lautsprecher."""
        import numpy as np

        device = self._device(output_key, AudioDirection.OUTPUT)
        count = int(TEST_TONE_RATE * TEST_TONE_SECONDS)
        t = np.arange(count, dtype=np.float32) / TEST_TONE_RATE
        tone = TEST_TONE_AMPLITUDE * np.sin(2.0 * math.pi * TEST_TONE_HZ * t)
        fade = int(TEST_TONE_RATE * 0.02)
        ramp = np.linspace(0.0, 1.0, fade, dtype=np.float32)
        tone[:fade] *= ramp
        tone[-fade:] *= ramp[::-1]
        self.manager.backend.play_samples(tone, output_index=device.index, sample_rate=TEST_TONE_RATE)
