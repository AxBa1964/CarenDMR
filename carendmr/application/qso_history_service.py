"""Persistente, UI-unabhängige QSO-Historie."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from carendmr.domain import CurrentCall, QsoHistoryEntry, QsoHistorySummary


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
                    timeslot INTEGER NOT NULL,
                    worked INTEGER NOT NULL DEFAULT 0,
                    worked_at TEXT NOT NULL DEFAULT ''
                )
                """
            )
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(qso_history)")}
            if "worked" not in columns:
                connection.execute("ALTER TABLE qso_history ADD COLUMN worked INTEGER NOT NULL DEFAULT 0")
            if "worked_at" not in columns:
                connection.execute("ALTER TABLE qso_history ADD COLUMN worked_at TEXT NOT NULL DEFAULT ''")
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_qso_history_ended_at ON qso_history(ended_at DESC)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_qso_history_source_id ON qso_history(source_id)"
            )
            connection.commit()

    def add_completed_call(self, call: CurrentCall) -> QsoHistoryEntry:
        ended = datetime.now(timezone.utc)
        started = ended.timestamp() - max(0.0, call.elapsed_seconds)
        started_text = datetime.fromtimestamp(started, timezone.utc).isoformat()
        contact = call.contact
        with self._lock, closing(self._connect()) as connection:
            previous = connection.execute(
                "SELECT MAX(worked) AS worked, MAX(worked_at) AS worked_at FROM qso_history WHERE source_id = ?",
                (call.source_id,),
            ).fetchone()
            worked = bool(previous["worked"] or 0)
            worked_at = str(previous["worked_at"] or "")
            cursor = connection.execute(
                """
                INSERT INTO qso_history (
                    started_at, ended_at, duration_seconds, source_id, callsign,
                    name, city, state, country, talkgroup, timeslot, worked, worked_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    started_text, ended.isoformat(), max(0.0, call.elapsed_seconds),
                    call.source_id, contact.callsign if contact else "",
                    contact.display_name if contact else "", contact.city if contact else "",
                    contact.state if contact else "", contact.country if contact else "",
                    call.talkgroup, call.timeslot, int(worked), worked_at,
                ),
            )
            connection.commit()
            entry_id = int(cursor.lastrowid)
        return QsoHistoryEntry(
            id=entry_id,
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
            worked=worked,
            worked_at=worked_at,
        )

    def list_recent(self, limit: int = 500) -> tuple[QsoHistoryEntry, ...]:
        if limit <= 0:
            raise ValueError("Das Historienlimit muss größer als null sein.")
        with self._lock, closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, started_at, ended_at, duration_seconds, source_id, callsign,
                       name, city, state, country, talkgroup, timeslot, worked, worked_at
                FROM qso_history
                ORDER BY ended_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return tuple(
            QsoHistoryEntry(**{**dict(row), "worked": bool(row["worked"])})
            for row in rows
        )

    def list_station_summaries(self, search: str = "", limit: int = 500) -> tuple[QsoHistorySummary, ...]:
        if limit <= 0:
            raise ValueError("Das Historienlimit muss größer als null sein.")
        entries = self.list_recent(limit=5000)
        query = search.strip().casefold()
        grouped: dict[int, dict[str, object]] = {}
        for entry in entries:
            item = grouped.get(entry.source_id)
            if item is None:
                item = {
                    "source_id": entry.source_id,
                    "callsign": entry.callsign,
                    "name": entry.name,
                    "city": entry.city,
                    "state": entry.state,
                    "country": entry.country,
                    "last_heard_at": entry.ended_at,
                    "last_talkgroup": entry.talkgroup,
                    "last_timeslot": entry.timeslot,
                    "heard_count": 0,
                    "total_duration_seconds": 0.0,
                    "worked": False,
                    "worked_at": "",
                }
                grouped[entry.source_id] = item
            item["heard_count"] = int(item["heard_count"]) + 1
            item["total_duration_seconds"] = float(item["total_duration_seconds"]) + entry.duration_seconds
            if entry.worked:
                item["worked"] = True
                if entry.worked_at and entry.worked_at > str(item["worked_at"]):
                    item["worked_at"] = entry.worked_at
        summaries = [QsoHistorySummary(**item) for item in grouped.values()]
        if query:
            summaries = [
                item for item in summaries
                if query in " ".join((
                    item.callsign, item.name, item.city, item.state, item.country,
                    str(item.source_id), str(item.last_talkgroup),
                )).casefold()
            ]
        summaries.sort(key=lambda item: item.last_heard_at, reverse=True)
        return tuple(summaries[:limit])

    def set_worked(self, source_id: int, worked: bool) -> None:
        if source_id <= 0:
            raise ValueError("Die DMR-ID muss größer als null sein.")
        worked_at = datetime.now(timezone.utc).isoformat() if worked else ""
        with self._lock, closing(self._connect()) as connection:
            connection.execute(
                "UPDATE qso_history SET worked = ?, worked_at = ? WHERE source_id = ?",
                (int(worked), worked_at, source_id),
            )
            connection.commit()

    def is_worked(self, source_id: int) -> bool:
        if source_id <= 0:
            return False
        with self._lock, closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT MAX(worked) AS worked FROM qso_history WHERE source_id = ?",
                (source_id,),
            ).fetchone()
        return bool(row["worked"] or 0)
