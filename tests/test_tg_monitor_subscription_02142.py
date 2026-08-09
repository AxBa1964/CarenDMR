from pathlib import Path
import unittest


class TGMonitorSubscription02142Tests(unittest.TestCase):
    def test_brandmeister_lastheard_subscribes_to_everything_after_connect(self):
        source = Path("carendmr/tg_monitor/activity_service.py").read_text(encoding="utf-8")
        self.assertIn('client.emit("join", "everything")', source)
        self.assertIn('SUBSCRIBE join=everything', source)


if __name__ == "__main__":
    unittest.main()
