from pathlib import Path
import unittest

from carendmr.ui.main_window import MainWindow


class OperationModel02464Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (Path(__file__).parents[1] / "carendmr" / "ui" / "main_window.py").read_text(encoding="utf-8")

    def test_talkgroup_is_spoken_digit_by_digit(self):
        self.assertEqual(MainWindow._spoken_talkgroup(26302), "zwei sechs drei null zwei")
        self.assertEqual(MainWindow._spoken_talkgroup("9990"), "neun neun neun null")

    def test_switch_button_is_removed(self):
        self.assertNotIn('text="TG wechseln"', self.source)

    def test_internal_reconnect_message_is_suppressed(self):
        self.assertIn('if message.code == "connection.connected":\n            return', self.source)

    def test_focus_moves_between_talkgroup_and_ptt(self):
        self.assertIn('self.root.after(0, self._focus_ptt_after_connect)', self.source)
        self.assertIn('self.talkgroup_entry.focus_set()', self.source)


if __name__ == "__main__":
    unittest.main()
