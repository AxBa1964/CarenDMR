"""Fachmodell für abgeschlossene private Parrot-Sendetests."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class TransmitHistoryEntry:
    started_at: str
    duration_seconds: float
    destination_id: int
    timeslot: int
    call_type: str
    echo_received: bool
    safety_limit_reached: bool
    optimizer_enabled: bool
