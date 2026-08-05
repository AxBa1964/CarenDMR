"""Lokale, plattformneutrale Quittungstöne für den Funkablauf.

Die Töne werden mathematisch erzeugt und über den bereits konfigurierten
CarenDMR-Wiedergabepfad abgespielt. Dadurch sind sie unabhängig von
Windows-Systemklängen und gelangen nicht in den Mikrofon-/Sendepfad.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from carendmr.audio.devices import AudioDirection


@dataclass(frozen=True, slots=True)
class ToneSpec:
    frequency_hz: float
    duration_seconds: float
    volume: float = 0.55


class AudioCuePlayer:
    """Erzeugt und spielt lokale TX-Quittungstöne."""

    SAMPLE_RATE = 44_100
    FADE_SECONDS = 0.008

    def __init__(self, audio_service: Any) -> None:
        self.audio_service = audio_service

    @classmethod
    def _tone(cls, spec: ToneSpec) -> np.ndarray:
        count = max(1, int(cls.SAMPLE_RATE * spec.duration_seconds))
        time_axis = np.linspace(0.0, spec.duration_seconds, count, endpoint=False, dtype=np.float32)
        samples = np.sin(2.0 * np.pi * spec.frequency_hz * time_axis).astype(np.float32)

        fade_count = min(count // 2, max(1, int(cls.SAMPLE_RATE * cls.FADE_SECONDS)))
        envelope = np.ones(count, dtype=np.float32)
        envelope[:fade_count] = np.linspace(0.0, 1.0, fade_count, dtype=np.float32)
        envelope[-fade_count:] = np.linspace(1.0, 0.0, fade_count, dtype=np.float32)
        return samples * envelope * float(spec.volume)

    @classmethod
    def _silence(cls, duration_seconds: float) -> np.ndarray:
        return np.zeros(max(1, int(cls.SAMPLE_RATE * duration_seconds)), dtype=np.float32)

    def _play(self, samples: np.ndarray) -> None:
        manager = self.audio_service.manager
        if not manager.devices:
            manager.scan()
        output = manager.resolve(AudioDirection.OUTPUT).device
        manager.backend.play_samples(samples, output_index=output.index, sample_rate=self.SAMPLE_RATE)

    def play_tx_start(self) -> None:
        """Ein klarer heller Beep unmittelbar vor dem tatsächlichen TX."""
        self._play(self._tone(ToneSpec(1_500.0, 0.16, 0.62)))

    def play_tx_stop(self) -> None:
        """Zwei kurze Beeps nach sicher beendetem Sendepfad."""
        beep = self._tone(ToneSpec(1_250.0, 0.075, 0.56))
        samples = np.concatenate((beep, self._silence(0.055), beep))
        self._play(samples)
