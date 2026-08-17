import tempfile
import unittest
from pathlib import Path

from carendmr.tg_monitor.activity_service import TalkgroupActivityService


class TGMonitorLogging02141Tests(unittest.TestCase):
    def test_log_writes_timestamped_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tg_monitor.log"
            service = TalkgroupActivityService(
                {91},
                on_activity=lambda _item: None,
                log_path=path,
            )
            service._log("TEST Nachricht")
            text = path.read_text(encoding="utf-8")
            self.assertIn("TEST Nachricht", text)

    def test_filter_change_is_logged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tg_monitor.log"
            service = TalkgroupActivityService(
                {91},
                on_activity=lambda _item: None,
                log_path=path,
            )
            service.set_monitored_talkgroups({91, 262})
            text = path.read_text(encoding="utf-8")
            self.assertIn("FILTER TGs=[91, 262]", text)


if __name__ == "__main__":
    unittest.main()
