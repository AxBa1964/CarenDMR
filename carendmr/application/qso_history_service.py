"""Persistente, UI-unabhängige QSO-Historie."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from carendmr.domain import CurrentCall, QsoHistoryEntry


class QsoHistoryService:
    def __init__(self, project_root: Path) -> None:
        self.database_path = Path(project_root) / "data" / "qso_history.db"
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10.0)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._lock, closing(self._connect()) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS qso_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    ended_at TEXT NOT NULL,
                    duration_seconds REAL NOT NULL,
                    source_id INTEGER NOT NULL,
                    callsign TEXT NOT NULL,
                    name TEXT NOT NULL,
                    city TEXT NOT NULL,
                    state TEXT NOT NULL,
                    country TEXT NOT NULL,
                    talkgroup INTEGER NOT NULL,
                    timeslot INTEGER NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_qso_history_ended_at ON qso_history(ended_at DESC)"
            )
            connection.commit()

    def add_completed_call(self, call: CurrentCall) -> QsoHistoryEntry:
        ended = datetime.now(timezone.utc)
        started = ended.timestamp() - max(0.0, call.elapsed_seconds)
        started_text = datetime.fromtimestamp(started, timezone.utc).isoformat()
        contact = call.contact
        entry = QsoHistoryEntry(
            started_at=started_text,
            ended_at=ended.isoformat(),
            duration_seconds=max(0.0, call.elapsed_seconds),
            source_id=call.source_id,
            callsign=contact.callsign if contact else "",
            name=contact.display_name if contact else "",
            city=contact.city if contact else "",
            state=contact.state if contact else "",
            country=contact.country if contact else "",
            talkgroup=call.talkgroup,
            timeslot=call.timeslot,
        )
        with self._lock, closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO qso_history (
                    started_at, ended_at, duration_seconds, source_id, callsign,
                    name, city, state, country, talkgroup, timeslot
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.started_at, entry.ended_at, entry.duration_seconds,
                    entry.source_id, entry.callsign, entry.name, entry.city,
                    entry.state, entry.country, entry.talkgroup, entry.timeslot,
                ),
            )
            connection.commit()
        return entry

    def list_recent(self, limit: int = 500) -> tuple[QsoHistoryEntry, ...]:
        if limit <= 0:
            raise ValueError("Das Historienlimit muss größer als null sein.")
        with self._lock, closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT started_at, ended_at, duration_seconds, source_id, callsign,
                       name, city, state, country, talkgroup, timeslot
                FROM qso_history
                ORDER BY ended_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return tuple(QsoHistoryEntry(**dict(row)) for row in rows)
