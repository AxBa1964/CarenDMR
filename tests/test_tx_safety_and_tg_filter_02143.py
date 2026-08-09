import json
import tempfile
import unittest
from pathlib import Path

from carendmr.application.audio_send_service import AudioSendService


class TxSafetyAndTGFilter02143Tests(unittest.TestCase):
    def test_historic_60_second_limit_is_migrated_to_300(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config"
            config.mkdir(parents=True)
            (config / "audio_send.local.json").write_text(
                json.dumps({"tx_safety_limit_seconds": 60}),
                encoding="utf-8",
            )
            service = AudioSendService(root, backend=object())
            self.assertEqual(300, service.tx_safety_limit_seconds)

    def test_default_tx_safety_limit_is_300_seconds(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = AudioSendService(Path(tmp), backend=object())
            self.assertEqual(300, service.tx_safety_limit_seconds)

    def test_tx_safety_maximum_is_300_seconds(self):
        self.assertEqual(300, AudioSendService.MAX_TX_SAFETY_LIMIT_SECONDS)

    def test_tg_monitor_has_three_second_default_filter(self):
        source = Path("carendmr/tg_monitor/window.py").read_text(encoding="utf-8")
        self.assertIn('settings.get("minimum_duration_seconds", 3)', source)
        self.assertIn('self.minimum_duration_spin.setValue(self._minimum_duration_seconds)', source)
        self.assertIn('if duration < self._minimum_duration_seconds:', source)


if __name__ == "__main__":
    unittest.main()
