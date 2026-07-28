"""Datenmodelle für Audio-Geräte und deren Auswahl."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class AudioDirection(str, Enum):
    INPUT = "input"
    OUTPUT = "output"


@dataclass(frozen=True, slots=True)
class AudioDevice:
    """Ein von PortAudio gemeldetes Audiogerät."""

    index: int
    name: str
    host_api: str
    max_input_channels: int
    max_output_channels: int
    default_sample_rate: float
    is_default_input: bool = False
    is_default_output: bool = False

    @property
    def supports_input(self) -> bool:
        return self.max_input_channels > 0

    @property
    def supports_output(self) -> bool:
        return self.max_output_channels > 0

    def supports(self, direction: AudioDirection) -> bool:
        if direction is AudioDirection.INPUT:
            return self.supports_input
        return self.supports_output

    @property
    def stable_key(self) -> str:
        """Stabilerer Schlüssel als der veränderliche PortAudio-Index."""
        return f"{self.host_api.strip().casefold()}|{self.name.strip().casefold()}"

    def display_name(self, direction: AudioDirection) -> str:
        marker = ""
        if direction is AudioDirection.INPUT and self.is_default_input:
            marker = "Standardgerät: "
        elif direction is AudioDirection.OUTPUT and self.is_default_output:
            marker = "Standardgerät: "
        return f"{marker}{self.name} ({self.host_api})"


@dataclass(frozen=True, slots=True)
class AudioSelection:
    """Persistierte Geräteidentität ohne Abhängigkeit vom Geräteindex."""

    name: str
    host_api: str
    direction: AudioDirection

    @property
    def stable_key(self) -> str:
        return f"{self.host_api.strip().casefold()}|{self.name.strip().casefold()}"

    @classmethod
    def from_device(
        cls,
        device: AudioDevice,
        direction: AudioDirection,
    ) -> "AudioSelection":
        if not device.supports(direction):
            raise ValueError(
                f"Das Gerät unterstützt die Richtung {direction.value} nicht."
            )
        return cls(
            name=device.name,
            host_api=device.host_api,
            direction=direction,
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["direction"] = self.direction.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AudioSelection":
        return cls(
            name=str(data["name"]),
            host_api=str(data["host_api"]),
            direction=AudioDirection(str(data["direction"])),
        )
