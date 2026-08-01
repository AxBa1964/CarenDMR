"""Fachmodell für abgeschlossene empfangene Sprechdurchgänge."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class QsoHistoryEntry:
    started_at: str
    ended_at: str
    duration_seconds: float
    source_id: int
    callsign: str
    name: str
    city: str
    state: str
    country: str
    talkgroup: int
    timeslot: int
