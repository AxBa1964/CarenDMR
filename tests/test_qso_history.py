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

class QsoHistoryWorkedTests(unittest.TestCase):
    def test_station_can_be_confirmed_as_worked_and_future_calls_inherit_status(self):
        with tempfile.TemporaryDirectory() as temp:
            service = QsoHistoryService(Path(temp))
            contact = RadioContact(2632198, "DO1DPL", "Axel", "Baruschke", city="Braunschweig", country="Germany")
            service.add_completed_call(CurrentCall(2632198, 91, 2, 7, 10.0, contact))
            service.set_worked(2632198, True)
            self.assertTrue(service.is_worked(2632198))
            service.add_completed_call(CurrentCall(2632198, 262, 1, 8, 5.0, contact))
            rows = service.list_recent()
            self.assertTrue(all(row.worked for row in rows))

    def test_station_summary_groups_speech_turns(self):
        with tempfile.TemporaryDirectory() as temp:
            service = QsoHistoryService(Path(temp))
            contact = RadioContact(1234567, "DL1ABC", "Max", "Muster", country="Germany")
            service.add_completed_call(CurrentCall(1234567, 91, 2, 1, 4.0, contact))
            service.add_completed_call(CurrentCall(1234567, 262, 1, 2, 6.0, contact))
            summaries = service.list_station_summaries("DL1ABC")
            self.assertEqual(1, len(summaries))
            self.assertEqual(2, summaries[0].heard_count)
            self.assertAlmostEqual(10.0, summaries[0].total_duration_seconds)
            self.assertEqual(262, summaries[0].last_talkgroup)
