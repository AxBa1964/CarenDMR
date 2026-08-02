import tempfile
import unittest
from pathlib import Path
from carendmr.application import TransmitHistoryService
from carendmr.domain import TransmitHistoryEntry

class TransmitHistoryTests(unittest.TestCase):
    def test_roundtrip_and_windows_safe_close(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            service = TransmitHistoryService(root)
            service.add(TransmitHistoryEntry(
                "2026-08-02T08:00:00+00:00", 4.2, 9990, 2, "Privatruf", True, False, True
            ))
            item = service.list_recent()[0]
            self.assertEqual(9990, item.destination_id)
            self.assertTrue(item.echo_received)
        self.assertFalse(root.exists())
