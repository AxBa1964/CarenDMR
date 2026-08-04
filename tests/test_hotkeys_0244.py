import tempfile
import unittest
from pathlib import Path

from carendmr.accessibility.hotkeys import DEFAULT_HOTKEYS, HotkeyManager


class HotkeyManager0244Tests(unittest.TestCase):
    def test_defaults_and_space_ptt(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = HotkeyManager(Path(directory) / "hotkeys.json")
            self.assertEqual(manager.mapping["PTT"], "Space")
            self.assertEqual(manager.mapping["TG_CHANGE"], "F2")

    def test_conflict_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = HotkeyManager(Path(directory) / "hotkeys.json")
            with self.assertRaises(ValueError):
                manager.set("STATUS", manager.mapping["TG_CHANGE"])

    def test_save_and_reload(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "hotkeys.json"
            manager = HotkeyManager(path)
            manager.set("STATUS", "Ctrl+I")
            self.assertEqual(HotkeyManager(path).mapping["STATUS"], "Ctrl+I")

    def test_sequences(self):
        self.assertEqual(HotkeyManager.tkinter_sequence("Space"), "<KeyPress-space>")
        self.assertEqual(HotkeyManager.tkinter_sequence("Space", release=True), "<KeyRelease-space>")
        self.assertEqual(HotkeyManager.tkinter_sequence("F2"), "<F2>")

    def test_no_default_conflicts(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = HotkeyManager(Path(directory) / "hotkeys.json")
            self.assertEqual(manager.conflicts(), [])
            self.assertEqual(set(manager.mapping), set(DEFAULT_HOTKEYS))

if __name__ == "__main__":
    unittest.main()
