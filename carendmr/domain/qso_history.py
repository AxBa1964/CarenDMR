"""Fachmodelle für empfangene Sprechdurchgänge und Stationszusammenfassungen."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class QsoHistoryEntry:
    id: int
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
    worked: bool = False
    worked_at: str = ""


@dataclass(frozen=True, slots=True)
class QsoHistorySummary:
    source_id: int
    callsign: str
    name: str
    city: str
    state: str
    country: str
    last_heard_at: str
    last_talkgroup: int
    last_timeslot: int
    heard_count: int
    total_duration_seconds: float
    worked: bool
    worked_at: str
