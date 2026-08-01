"""Sicherer CSV-Import in eine neue SQLite-Datenbank."""

from __future__ import annotations

import csv
import os
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ContactImportResult:
    record_count: int
    updated_at: str


_ALIASES = {
    "dmr_id": ("RADIO_ID", "DMR_ID", "ID", "radio_id", "dmr_id", "id"),
    "callsign": ("CALLSIGN", "callsign", "Callsign"),
    "first_name": ("FIRST_NAME", "FIRSTNAME", "first_name", "fname"),
    "last_name": ("LAST_NAME", "LASTNAME", "last_name", "surname"),
    "city": ("CITY", "city"),
    "state": ("STATE", "state"),
    "country": ("COUNTRY", "country"),
    "remarks": ("REMARKS", "remarks"),
}


def _value(row: dict[str, str | None], field: str) -> str:
    for alias in _ALIASES[field]:
        value = row.get(alias)
        if value is not None:
            return value.strip()
    return ""


class RadioIdCsvImporter:
    def import_atomic(self, csv_path: Path, database_path: Path) -> ContactImportResult:
        csv_path = Path(csv_path)
        database_path = Path(database_path)
        database_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = database_path.with_suffix(database_path.suffix + ".tmp")
        temporary_path.unlink(missing_ok=True)
        updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        count = 0
        try:
            with closing(sqlite3.connect(temporary_path)) as connection:
                connection.executescript(
                    """
                    PRAGMA journal_mode=DELETE;
                    CREATE TABLE contacts (
                        dmr_id INTEGER PRIMARY KEY,
                        callsign TEXT NOT NULL,
                        first_name TEXT NOT NULL,
                        last_name TEXT NOT NULL,
                        city TEXT NOT NULL,
                        state TEXT NOT NULL,
                        country TEXT NOT NULL,
                        remarks TEXT NOT NULL
                    );
                    CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                    """
                )
                with csv_path.open("r", encoding="utf-8-sig", newline="") as source:
                    reader = csv.DictReader(source)
                    if not reader.fieldnames:
                        raise ValueError("Der RadioID-Export enthält keine Spaltenüberschriften.")
                    rows: list[tuple[object, ...]] = []
                    for row in reader:
                        raw_id = _value(row, "dmr_id")
                        callsign = _value(row, "callsign").upper()
                        if not raw_id.isdigit() or not callsign:
                            continue
                        rows.append((
                            int(raw_id), callsign, _value(row, "first_name"),
                            _value(row, "last_name"), _value(row, "city"),
                            _value(row, "state"), _value(row, "country"),
                            _value(row, "remarks"),
                        ))
                        if len(rows) >= 5000:
                            connection.executemany(
                                "INSERT OR REPLACE INTO contacts VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows
                            )
                            count += len(rows)
                            rows.clear()
                    if rows:
                        connection.executemany(
                            "INSERT OR REPLACE INTO contacts VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows
                        )
                        count += len(rows)
                count = int(connection.execute("SELECT COUNT(*) FROM contacts").fetchone()[0])
                if count == 0:
                    raise ValueError("Der RadioID-Export enthält keine gültigen DMR-Kontakte.")
                connection.executemany(
                    "INSERT INTO metadata(key, value) VALUES (?, ?)",
                    (("source", "RadioID.net"), ("updated_at", updated_at), ("record_count", str(count))),
                )
                connection.commit()
            os.replace(temporary_path, database_path)
            return ContactImportResult(count, updated_at)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise
