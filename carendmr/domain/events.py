"""Neutrale Anwendungsereignisse ohne GUI- oder Netzwerkabhängigkeit."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class EventLevel(str, Enum):
    INFO = "Information"
    WARNING = "Warnung"
    ERROR = "Fehler"


@dataclass(frozen=True, slots=True)
class ApplicationEvent:
    timestamp: datetime
    message: str
    level: EventLevel = EventLevel.INFO

    @property
    def display_text(self) -> str:
        return f"{self.timestamp:%H:%M:%S} – {self.level.value}: {self.message}"
