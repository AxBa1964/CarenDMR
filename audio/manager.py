"""Robuste Verwaltung, Auswahl und Prüfung von Audiogeräten."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .backend import AudioBackend
from .config import AudioConfigStore
from .devices import AudioDevice, AudioDirection, AudioSelection


class AudioUnavailableError(RuntimeError):
    """Ein benötigtes Audio-Gerät ist nicht verfügbar."""


class AudioConfigurationError(RuntimeError):
    """Die lokale Audio-Konfiguration ist ungültig."""


@dataclass(frozen=True, slots=True)
class ResolvedAudioDevice:
    device: AudioDevice
    used_fallback: bool
    message: str


class AudioManager:
    """Erkennt Geräte und löst gespeicherte Auswahl robust auf."""

    def __init__(
        self,
        backend: AudioBackend,
        config_path: Path,
    ) -> None:
        self.backend = backend
        self.store = AudioConfigStore(config_path)
        self._devices: list[AudioDevice] = []

    @property
    def devices(self) -> tuple[AudioDevice, ...]:
        return tuple(self._devices)

    def scan(self) -> tuple[AudioDevice, ...]:
        self._devices = self.backend.query_devices()
        return self.devices

    def list_devices(
        self,
        direction: AudioDirection,
    ) -> tuple[AudioDevice, ...]:
        return tuple(
            device for device in self._devices if device.supports(direction)
        )

    def default_device(
        self,
        direction: AudioDirection,
    ) -> AudioDevice | None:
        for device in self.list_devices(direction):
            if (
                direction is AudioDirection.INPUT
                and device.is_default_input
            ):
                return device
            if (
                direction is AudioDirection.OUTPUT
                and device.is_default_output
            ):
                return device
        return None

    def find_selection(
        self,
        selection: AudioSelection,
    ) -> AudioDevice | None:
        for device in self.list_devices(selection.direction):
            if device.stable_key == selection.stable_key:
                return device
        return None

    def save_selection(
        self,
        input_device: AudioDevice,
        output_device: AudioDevice,
    ) -> None:
        selections = {
            AudioDirection.INPUT: AudioSelection.from_device(
                input_device,
                AudioDirection.INPUT,
            ),
            AudioDirection.OUTPUT: AudioSelection.from_device(
                output_device,
                AudioDirection.OUTPUT,
            ),
        }
        self.store.save(selections)

    def resolve(
        self,
        direction: AudioDirection,
    ) -> ResolvedAudioDevice:
        try:
            selections = self.store.load()
        except ValueError as exc:
            raise AudioConfigurationError(str(exc)) from exc

        selected = selections.get(direction)
        if selected is not None:
            device = self.find_selection(selected)
            if device is not None:
                return ResolvedAudioDevice(
                    device=device,
                    used_fallback=False,
                    message=(
                        f"Gespeichertes {self._direction_word(direction)} "
                        f"gefunden: {device.name}."
                    ),
                )

        fallback = self.default_device(direction)
        if fallback is None:
            available = self.list_devices(direction)
            fallback = available[0] if available else None

        if fallback is None:
            raise AudioUnavailableError(
                f"Es wurde kein {self._direction_word(direction)} gefunden. "
                f"Bitte schließen Sie ein geeignetes Gerät an und starten "
                f"Sie die Prüfung erneut."
            )

        if selected is None:
            message = (
                f"Es wurde noch kein {self._direction_word(direction)} "
                f"gespeichert. Verwendet wird {fallback.name}."
            )
        else:
            message = (
                f"Das gespeicherte {self._direction_word(direction)} "
                f"'{selected.name}' ist nicht verfügbar. "
                f"Verwendet wird stattdessen {fallback.name}."
            )
        return ResolvedAudioDevice(
            device=fallback,
            used_fallback=True,
            message=message,
        )

    def run_loopback_test(
        self,
        *,
        duration_seconds: float = 4.0,
        sample_rate: int = 48000,
    ) -> tuple[ResolvedAudioDevice, ResolvedAudioDevice]:
        if not self._devices:
            self.scan()
        input_result = self.resolve(AudioDirection.INPUT)
        output_result = self.resolve(AudioDirection.OUTPUT)

        channels = min(
            1,
            input_result.device.max_input_channels,
            output_result.device.max_output_channels,
        )
        if channels < 1:
            raise AudioUnavailableError(
                "Die ausgewählten Geräte unterstützen keinen gemeinsamen "
                "Audiokanal."
            )

        self.backend.record_and_play(
            input_index=input_result.device.index,
            output_index=output_result.device.index,
            duration_seconds=duration_seconds,
            sample_rate=sample_rate,
            channels=channels,
        )
        return input_result, output_result

    @staticmethod
    def _direction_word(direction: AudioDirection) -> str:
        if direction is AudioDirection.INPUT:
            return "Mikrofon"
        return "Wiedergabegerät"
