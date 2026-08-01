"""Fachmodell eines lokal aufgelösten DMR-Kontakts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RadioContact:
    dmr_id: int
    callsign: str
    first_name: str = ""
    last_name: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    remarks: str = ""

    @property
    def display_name(self) -> str:
        return " ".join(part for part in (self.first_name, self.last_name) if part).strip()

    @property
    def spoken_identity(self) -> str:
        parts = [self.callsign or f"DMR-ID {self.dmr_id}"]
        if self.display_name:
            parts.append(self.display_name)
        if self.country:
            parts.append(self.country)
        return ", ".join(parts)
