import io
import tempfile
import unittest
from pathlib import Path

from carendmr.contacts import RadioIdCsvImporter, RadioIdDownloader, SqliteContactRepository


CSV = """RADIO_ID,CALLSIGN,FIRST_NAME,LAST_NAME,CITY,STATE,COUNTRY,REMARKS
2632198,DO1DPL,Axel,Baruschke,Braunschweig,Niedersachsen,Germany,
2342444,G4ABC,Anne,Example,London,,United Kingdom,
"""


class ContactImportTests(unittest.TestCase):
    def test_atomic_import_lookup_and_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            csv_path = root / "users.csv"
            database = root / "data" / "contacts.db"
            csv_path.write_text(CSV, encoding="utf-8")

            result = RadioIdCsvImporter().import_atomic(csv_path, database)
            repository = SqliteContactRepository(database)
            contact = repository.lookup(2632198)

            self.assertEqual(2, result.record_count)
            self.assertEqual("DO1DPL", contact.callsign)
            self.assertEqual("Axel Baruschke", contact.display_name)
            self.assertEqual(2, repository.info().record_count)
            self.assertFalse(database.with_suffix(".db.tmp").exists())

    def test_invalid_import_keeps_existing_database(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            valid = root / "valid.csv"
            invalid = root / "invalid.csv"
            database = root / "contacts.db"
            valid.write_text(CSV, encoding="utf-8")
            invalid.write_text("broken\nvalue\n", encoding="utf-8")
            importer = RadioIdCsvImporter()
            importer.import_atomic(valid, database)

            with self.assertRaises(ValueError):
                importer.import_atomic(invalid, database)

            self.assertEqual("DO1DPL", SqliteContactRepository(database).lookup(2632198).callsign)
            self.assertFalse(database.with_suffix(".db.tmp").exists())


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


class ContactDownloadTests(unittest.TestCase):
    def test_download_uses_target_and_finishes_atomically(self):
        requests = []

        def opener(request, timeout):
            requests.append((request, timeout))
            return _Response(CSV.encode("utf-8"))

        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "radioid.csv"
            RadioIdDownloader(opener).download(target)
            self.assertEqual(CSV, target.read_text(encoding="utf-8"))
            self.assertFalse(target.with_suffix(".csv.part").exists())
            self.assertIn("CarenDMR/0.2.0", requests[0][0].headers["User-agent"])


if __name__ == "__main__":
    unittest.main()
