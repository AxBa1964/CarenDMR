import tempfile
import unittest
from pathlib import Path

from carendmr.application import QsoHistoryService
from carendmr.domain import CurrentCall, RadioContact


class QsoHistoryTests(unittest.TestCase):
    def test_completed_call_is_persisted_and_loaded(self):
        with tempfile.TemporaryDirectory() as temp:
            service = QsoHistoryService(Path(temp))
            contact = RadioContact(2632198, "DO1DPL", "Axel", "Baruschke", city="Braunschweig", country="Germany")
            service.add_completed_call(CurrentCall(2632198, 91, 2, 7, 14.2, contact))
            rows = service.list_recent()
        self.assertEqual(1, len(rows))
        self.assertEqual("DO1DPL", rows[0].callsign)
        self.assertEqual(2632198, rows[0].source_id)
        self.assertAlmostEqual(14.2, rows[0].duration_seconds)

    def test_database_connection_is_closed_for_windows_cleanup(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            service = QsoHistoryService(root)
            service.add_completed_call(CurrentCall(123, 91, 2, None, 1.0))
            database = service.database_path
            database.unlink()
            self.assertFalse(database.exists())


if __name__ == "__main__":
    unittest.main()
