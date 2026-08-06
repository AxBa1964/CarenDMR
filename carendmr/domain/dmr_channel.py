"""Fachliches Modell eines in CarenDMR verwendeten DMR-Kanals."""
from __future__ import annotations

from dataclasses import dataclass


_VALID_CALL_TYPES = {"group", "private"}


@dataclass(frozen=True, slots=True)
class DmrChannel:
    """Kombination aus Ziel, Timeslot und Rufart.

    ``target`` ist bei Gruppenrufen die Talkgroup und bei Privatrufen die
    DMR-ID. Der optionale Name wird später für Verzeichnis und Favoriten
    verwendet, ohne die Funkparameter zu verändern.
    """

    target: int
    timeslot: int
    call_type: str
    name: str = ""
    country: str = ""
    description: str = ""
    language: str = ""
    language_source: str = ""
    language_confidence: float = 0.0

    def normalized(self) -> "DmrChannel":
        target = int(self.target)
        if target <= 0:
            raise ValueError("Talkgroup oder DMR-ID muss größer als 0 sein.")
        if self.timeslot not in {1, 2}:
            raise ValueError("Timeslot muss 1 oder 2 sein.")
        call_type = str(self.call_type).strip().lower()
        if call_type not in _VALID_CALL_TYPES:
            raise ValueError("Rufart muss 'group' oder 'private' sein.")
        return DmrChannel(
            target=target,
            timeslot=self.timeslot,
            call_type=call_type,
            name=str(self.name).strip(),
            country=str(self.country).strip(),
            description=str(self.description).strip(),
            language=str(self.language).strip(),
            language_source=str(self.language_source).strip(),
            language_confidence=max(0.0, min(1.0, float(self.language_confidence))),
        )

    @property
    def is_group_call(self) -> bool:
        return self.call_type == "group"

    @property
    def target_label(self) -> str:
        return "Talkgroup" if self.is_group_call else "DMR-ID"
