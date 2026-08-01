"""Fachmodell für den aktuell empfangenen DMR-Sprechdurchgang."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .radio_contact import RadioContact


@dataclass(frozen=True, slots=True)
class CurrentCall:
    """UI-unabhängige Angaben zum aktuellen Sprecher."""

    source_id: int
    talkgroup: int
    timeslot: int
    stream_id: int | None
    elapsed_seconds: float = 0.0
    contact: RadioContact | None = None

    def with_elapsed(self, elapsed_seconds: float) -> "CurrentCall":
        return replace(self, elapsed_seconds=max(0.0, elapsed_seconds))
