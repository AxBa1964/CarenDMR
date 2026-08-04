"""Strukturierte Informationen für visuelle und sprachliche Ausgabekanäle."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Mapping

from .events import EventLevel


class InformationCategory(str, Enum):
    SYSTEM = "System"
    CONNECTION = "Verbindung"
    NETWORK = "Netzwerk"
    AUDIO = "Audio"
    TRANSMISSION = "Senden"
    RECEPTION = "Empfang"
    RADIO = "Funkbetrieb"
    OPERATION = "Bedienung"
    QSO = "QSO"
    SETTINGS = "Einstellungen"
    DIAGNOSTICS = "Diagnose"
    WARNING = "Warnung"
    ERROR = "Fehler"


class InformationPriority(str, Enum):
    DEBUG = "Debug"
    LOW = "Niedrig"
    NORMAL = "Normal"
    HIGH = "Hoch"
    WARNING = "Warnung"
    ERROR = "Fehler"
    CRITICAL = "Kritisch"


class OperatingContext(str, Enum):
    UNKNOWN = "Unbekannt"
    OPERATION = "Betrieb"
    QSO_HISTORY = "QSO-Historie"
    SETTINGS = "Einstellungen"
    DIAGNOSTICS = "Diagnose"
    AUDIO = "Audio"


@dataclass(frozen=True, slots=True)
class InformationMessage:
    """Eine fachliche Meldung, unabhängig von GUI, TTS oder Gerätedisplay."""

    timestamp: datetime
    code: str
    short_text: str
    long_text: str
    category: InformationCategory = InformationCategory.SYSTEM
    priority: InformationPriority = InformationPriority.NORMAL
    level: EventLevel = EventLevel.INFO
    action_hint: str | None = None
    speak: bool = True
    context: OperatingContext = OperatingContext.UNKNOWN
    metadata: Mapping[str, object] | None = None

    @property
    def visual_text(self) -> str:
        return f"{self.timestamp:%H:%M:%S} – {self.level.value}: {self.short_text}"

    @property
    def speech_text(self) -> str:
        base = self.long_text.strip() or self.short_text.strip()
        if self.action_hint:
            return f"{base} {self.action_hint}".strip()
        return base
