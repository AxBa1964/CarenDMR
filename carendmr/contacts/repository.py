"""SQLite-Repository für lokale DMR-Kontakte."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from carendmr.domain.radio_contact import RadioContact


@dataclass(frozen=True, slots=True)
class ContactDatabaseInfo:
    source: str = "RadioID.net"
    updated_at: str = ""
    record_count: int = 0


class SqliteContactRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)

    def lookup(self, dmr_id: int) -> RadioContact | None:
        if dmr_id <= 0 or not self.database_path.is_file():
            return None
        with closing(sqlite3.connect(self.database_path)) as connection:
            row = connection.execute(
                """
                SELECT dmr_id, callsign, first_name, last_name, city, state, country, remarks
                FROM contacts WHERE dmr_id = ?
                """,
                (dmr_id,),
            ).fetchone()
        return RadioContact(*row) if row else None

    def info(self) -> ContactDatabaseInfo:
        if not self.database_path.is_file():
            return ContactDatabaseInfo()
        with closing(sqlite3.connect(self.database_path)) as connection:
            values = dict(connection.execute("SELECT key, value FROM metadata").fetchall())
        return ContactDatabaseInfo(
            source=values.get("source", "RadioID.net"),
            updated_at=values.get("updated_at", ""),
            record_count=int(values.get("record_count", "0")),
        )
