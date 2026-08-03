"""Neutrale Anwendungsereignisse ohne GUI- oder Netzwerkabhängigkeit."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .information import InformationMessage


class EventLevel(str, Enum):
    INFO = "Information"
    WARNING = "Warnung"
    ERROR = "Fehler"


@dataclass(frozen=True, slots=True)
class ApplicationEvent:
    timestamp: datetime
    message: str
    level: EventLevel = EventLevel.INFO
    code: str = "general.message"
    speech_text: str | None = None

    @property
    def display_text(self) -> str:
        return f"{self.timestamp:%H:%M:%S} – {self.level.value}: {self.message}"

    @classmethod
    def from_information(cls, information: "InformationMessage") -> "ApplicationEvent":
        return cls(
            timestamp=information.timestamp,
            message=information.short_text,
            level=information.level,
            code=information.code,
            speech_text=information.speech_text,
        )
