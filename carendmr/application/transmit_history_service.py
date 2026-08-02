"""Lokale, plattformneutrale Historie für Parrot-Sendetests."""
from __future__ import annotations
import sqlite3
from contextlib import closing
from pathlib import Path
from carendmr.domain.transmit_history import TransmitHistoryEntry

class TransmitHistoryService:
    def __init__(self, project_root: Path) -> None:
        self.database_path = Path(project_root) / 'data' / 'transmit_history.db'
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute('''CREATE TABLE IF NOT EXISTS transmit_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                duration_seconds REAL NOT NULL,
                destination_id INTEGER NOT NULL,
                timeslot INTEGER NOT NULL,
                call_type TEXT NOT NULL,
                echo_received INTEGER NOT NULL,
                safety_limit_reached INTEGER NOT NULL,
                optimizer_enabled INTEGER NOT NULL
            )''')
            connection.commit()

    def add(self, entry: TransmitHistoryEntry) -> None:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute('''INSERT INTO transmit_history
                (started_at,duration_seconds,destination_id,timeslot,call_type,echo_received,safety_limit_reached,optimizer_enabled)
                VALUES (?,?,?,?,?,?,?,?)''', (
                entry.started_at, entry.duration_seconds, entry.destination_id, entry.timeslot,
                entry.call_type, int(entry.echo_received), int(entry.safety_limit_reached),
                int(entry.optimizer_enabled),
            ))
            connection.commit()

    def list_recent(self, limit: int = 200) -> tuple[TransmitHistoryEntry, ...]:
        with closing(sqlite3.connect(self.database_path)) as connection:
            rows = connection.execute('''SELECT started_at,duration_seconds,destination_id,timeslot,call_type,
                echo_received,safety_limit_reached,optimizer_enabled FROM transmit_history
                ORDER BY id DESC LIMIT ?''', (limit,)).fetchall()
        return tuple(TransmitHistoryEntry(r[0], float(r[1]), int(r[2]), int(r[3]), str(r[4]), bool(r[5]), bool(r[6]), bool(r[7])) for r in rows)
