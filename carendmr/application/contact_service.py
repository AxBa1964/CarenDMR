"""Anwendungsschicht für Lookup und Aktualisierung der Kontaktdatenbank."""

from __future__ import annotations

from pathlib import Path

from carendmr.contacts import RadioIdCsvImporter, RadioIdDownloader, SqliteContactRepository
from carendmr.domain.radio_contact import RadioContact


class ContactService:
    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root)
        self.database_path = self.project_root / "data" / "contacts.db"
        self.repository = SqliteContactRepository(self.database_path)

    def lookup(self, dmr_id: int) -> RadioContact | None:
        return self.repository.lookup(dmr_id)

    def update(self) -> tuple[int, str]:
        download_path = self.project_root / "data" / "radioid_user.csv"
        RadioIdDownloader().download(download_path)
        try:
            result = RadioIdCsvImporter().import_atomic(download_path, self.database_path)
        finally:
            download_path.unlink(missing_ok=True)
        return result.record_count, result.updated_at

    def info(self):
        return self.repository.info()
