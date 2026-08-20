"""Persistente, UI-unabhängige QSO-Historie."""

from __future__ import annotations

import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from carendmr.domain import CurrentCall, QsoHistoryEntry, QsoHistorySummary
from carendmr.qso_sync import QsoSyncStore


class QsoHistoryService:
    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root)
        self.database_path = self.project_root / "data" / "qso_history.db"
        self._sync_store = QsoSyncStore(self.project_root)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._added_callbacks = []
        self._initialize()
        self.sync_now(best_effort=True)

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
                    worked_at TEXT NOT NULL DEFAULT '',
                    sync_id TEXT NOT NULL DEFAULT ''
                )
                """
            )
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(qso_history)")}
            if "worked" not in columns:
                connection.execute("ALTER TABLE qso_history ADD COLUMN worked INTEGER NOT NULL DEFAULT 0")
            if "worked_at" not in columns:
                connection.execute("ALTER TABLE qso_history ADD COLUMN worked_at TEXT NOT NULL DEFAULT ''")
            if "sync_id" not in columns:
                connection.execute("ALTER TABLE qso_history ADD COLUMN sync_id TEXT NOT NULL DEFAULT ''")
            missing = connection.execute("SELECT id FROM qso_history WHERE sync_id = ''").fetchall()
            for row in missing:
                connection.execute("UPDATE qso_history SET sync_id = ? WHERE id = ?", (uuid.uuid4().hex, int(row["id"])))
            connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_qso_history_sync_id ON qso_history(sync_id)")
            connection.execute(
                """CREATE TABLE IF NOT EXISTS qso_sync_state (
                    source_id INTEGER PRIMARY KEY, worked INTEGER NOT NULL DEFAULT 0,
                    changed_at TEXT NOT NULL DEFAULT ''
                )"""
            )
            for row in connection.execute("SELECT source_id, MAX(worked) AS worked, MAX(worked_at) AS worked_at FROM qso_history GROUP BY source_id"):
                connection.execute(
                    "INSERT OR IGNORE INTO qso_sync_state (source_id, worked, changed_at) VALUES (?, ?, ?)",
                    (int(row["source_id"]), int(row["worked"] or 0), str(row["worked_at"] or "")),
                )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_qso_history_ended_at ON qso_history(ended_at DESC)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_qso_history_source_id ON qso_history(source_id)"
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS qrz_logbook (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id INTEGER NOT NULL, callsign TEXT NOT NULL,
                    qso_at TEXT NOT NULL, logid TEXT NOT NULL, logged_at TEXT NOT NULL,
                    UNIQUE(callsign, qso_at)
                )"""
            )
            connection.commit()

    def subscribe_added(self, callback) -> None:
        """Benachrichtigt UIs unmittelbar nachdem ein Empfang in SQLite gespeichert ist."""
        self._added_callbacks.append(callback)

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
                    name, city, state, country, talkgroup, timeslot, worked, worked_at, sync_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    started_text, ended.isoformat(), max(0.0, call.elapsed_seconds),
                    call.source_id, contact.callsign if contact else "",
                    contact.display_name if contact else "", contact.city if contact else "",
                    contact.state if contact else "", contact.country if contact else "",
                    call.talkgroup, call.timeslot, int(worked), worked_at, uuid.uuid4().hex,
                ),
            )
            connection.commit()
            entry_id = int(cursor.lastrowid)
        entry = QsoHistoryEntry(
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
        for callback in tuple(self._added_callbacks):
            try:
                callback(entry)
            except Exception:
                pass
        self.sync_now(best_effort=True)
        return entry

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
            connection.execute(
                "INSERT INTO qso_sync_state (source_id, worked, changed_at) VALUES (?, ?, ?) "
                "ON CONFLICT(source_id) DO UPDATE SET worked=excluded.worked, changed_at=excluded.changed_at",
                (source_id, int(worked), datetime.now(timezone.utc).isoformat()),
            )
            connection.commit()
        self.sync_now(best_effort=True)

    def last_worked_at(self, source_id: int) -> str:
        if source_id <= 0:
            return ""
        with self._lock, closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT MAX(worked_at) AS worked_at FROM qso_history "
                "WHERE source_id = ? AND worked = 1",
                (source_id,),
            ).fetchone()
        return str(row["worked_at"] or "")

    def mark_worked(
        self,
        source_id: int,
        *,
        callsign: str = "",
        name: str = "",
        city: str = "",
        state: str = "",
        country: str = "",
        talkgroup: int = 0,
        timeslot: int = 2,
    ) -> str:
        """Markiert eine Station jetzt als gesprochen.

        Falls sie noch nicht in der Empfangshistorie steht, wird ein kompakter
        manueller Eintrag erzeugt. So funktioniert der Button auch während des
        ersten laufenden QSO.
        """
        if source_id <= 0:
            raise ValueError("Die DMR-ID muss größer als null sein.")
        worked_at = datetime.now(timezone.utc).isoformat()
        with self._lock, closing(self._connect()) as connection:
            count = int(connection.execute(
                "SELECT COUNT(*) AS count FROM qso_history WHERE source_id = ?",
                (source_id,),
            ).fetchone()["count"])
            if count:
                connection.execute(
                    "UPDATE qso_history SET worked = 1, worked_at = ? WHERE source_id = ?",
                    (worked_at, source_id),
                )
            else:
                connection.execute(
                    """
                    INSERT INTO qso_history (
                        started_at, ended_at, duration_seconds, source_id, callsign,
                        name, city, state, country, talkgroup, timeslot, worked, worked_at, sync_id
                    ) VALUES (?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                    """,
                    (
                        worked_at, worked_at, source_id, callsign, name, city, state,
                        country, max(0, int(talkgroup)), int(timeslot), worked_at, uuid.uuid4().hex,
                    ),
                )
            connection.execute(
                "INSERT INTO qso_sync_state (source_id, worked, changed_at) VALUES (?, 1, ?) "
                "ON CONFLICT(source_id) DO UPDATE SET worked=1, changed_at=excluded.changed_at",
                (source_id, worked_at),
            )
            connection.commit()
        self.sync_now(best_effort=True)
        return worked_at

    def record_qrz_log(self, source_id: int, callsign: str, qso_at: str, logid: str) -> None:
        logged_at = datetime.now(timezone.utc).isoformat()
        with self._lock, closing(self._connect()) as connection:
            connection.execute(
                "INSERT OR REPLACE INTO qrz_logbook (source_id, callsign, qso_at, logid, logged_at) VALUES (?, ?, ?, ?, ?)",
                (int(source_id), callsign.strip().upper(), qso_at, str(logid), logged_at),
            )
            connection.commit()
        self.sync_now(best_effort=True)

    def qrz_logid(self, callsign: str, qso_at: str) -> str:
        with self._lock, closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT logid FROM qrz_logbook WHERE callsign = ? AND qso_at = ?",
                (callsign.strip().upper(), qso_at),
            ).fetchone()
        return str(row["logid"] if row else "")

    def sync_now(self, *, best_effort: bool = False) -> str:
        """Importiert Peer-Snapshots und veröffentlicht danach den lokalen Gesamtstand."""
        try:
            if not self._sync_store.config.enabled:
                return "QSO-Synchronisation ist deaktiviert."
            peers = self._sync_store.peer_snapshots()
            imported_entries = 0
            imported_states = 0
            imported_logs = 0
            with self._lock, closing(self._connect()) as connection:
                for snapshot in peers:
                    for item in snapshot.get("entries", []):
                        sync_id = str(item.get("sync_id", "")).strip()
                        if not sync_id:
                            continue
                        exists = connection.execute("SELECT 1 FROM qso_history WHERE sync_id = ?", (sync_id,)).fetchone()
                        if exists:
                            continue
                        connection.execute(
                            """INSERT INTO qso_history (started_at, ended_at, duration_seconds, source_id, callsign,
                               name, city, state, country, talkgroup, timeslot, worked, worked_at, sync_id)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (str(item.get("started_at", "")), str(item.get("ended_at", "")), float(item.get("duration_seconds", 0.0)),
                             int(item.get("source_id", 0)), str(item.get("callsign", "")), str(item.get("name", "")),
                             str(item.get("city", "")), str(item.get("state", "")), str(item.get("country", "")),
                             int(item.get("talkgroup", 0)), int(item.get("timeslot", 2)), int(bool(item.get("worked", False))),
                             str(item.get("worked_at", "")), sync_id),
                        )
                        imported_entries += 1
                    for state in snapshot.get("station_states", []):
                        source_id = int(state.get("source_id", 0))
                        if source_id <= 0:
                            continue
                        remote_changed = str(state.get("changed_at", ""))
                        local = connection.execute("SELECT worked, changed_at FROM qso_sync_state WHERE source_id = ?", (source_id,)).fetchone()
                        if local is not None and str(local["changed_at"] or "") >= remote_changed:
                            continue
                        worked = int(bool(state.get("worked", False)))
                        connection.execute(
                            "INSERT INTO qso_sync_state (source_id, worked, changed_at) VALUES (?, ?, ?) "
                            "ON CONFLICT(source_id) DO UPDATE SET worked=excluded.worked, changed_at=excluded.changed_at",
                            (source_id, worked, remote_changed),
                        )
                        connection.execute(
                            "UPDATE qso_history SET worked = ?, worked_at = ? WHERE source_id = ?",
                            (worked, remote_changed if worked else "", source_id),
                        )
                        imported_states += 1
                    for log in snapshot.get("qrz_logs", []):
                        callsign = str(log.get("callsign", "")).strip().upper()
                        qso_at = str(log.get("qso_at", ""))
                        if not callsign or not qso_at:
                            continue
                        existing = connection.execute("SELECT logged_at FROM qrz_logbook WHERE callsign = ? AND qso_at = ?", (callsign, qso_at)).fetchone()
                        remote_logged = str(log.get("logged_at", ""))
                        if existing is not None and str(existing["logged_at"] or "") >= remote_logged:
                            continue
                        connection.execute(
                            "INSERT INTO qrz_logbook (source_id, callsign, qso_at, logid, logged_at) VALUES (?, ?, ?, ?, ?) "
                            "ON CONFLICT(callsign, qso_at) DO UPDATE SET source_id=excluded.source_id, logid=excluded.logid, logged_at=excluded.logged_at",
                            (int(log.get("source_id", 0)), callsign, qso_at, str(log.get("logid", "")), remote_logged),
                        )
                        imported_logs += 1
                # Nach importierten Einträgen vorhandene Stationszustände anwenden.
                for state in connection.execute("SELECT source_id, worked, changed_at FROM qso_sync_state"):
                    connection.execute(
                        "UPDATE qso_history SET worked = ?, worked_at = ? WHERE source_id = ?",
                        (int(state["worked"]), str(state["changed_at"] or "") if state["worked"] else "", int(state["source_id"])),
                    )
                connection.commit()
                entries = [dict(row) for row in connection.execute(
                    "SELECT started_at, ended_at, duration_seconds, source_id, callsign, name, city, state, country, talkgroup, timeslot, worked, worked_at, sync_id FROM qso_history ORDER BY ended_at"
                )]
                states = [dict(row) for row in connection.execute("SELECT source_id, worked, changed_at FROM qso_sync_state ORDER BY source_id")]
                logs = [dict(row) for row in connection.execute("SELECT source_id, callsign, qso_at, logid, logged_at FROM qrz_logbook ORDER BY qso_at")]
            self._sync_store.write_snapshot({"entries": entries, "station_states": states, "qrz_logs": logs})
            return f"Synchronisiert: {imported_entries} Historieneinträge, {imported_states} QSO-Status, {imported_logs} QRZ-Status übernommen."
        except Exception as exc:
            if best_effort:
                return f"QSO-Synchronisation übersprungen: {exc}"
            raise

    def is_worked(self, source_id: int) -> bool:
        if source_id <= 0:
            return False
        with self._lock, closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT MAX(worked) AS worked FROM qso_history WHERE source_id = ?",
                (source_id,),
            ).fetchone()
        return bool(row["worked"] or 0)
