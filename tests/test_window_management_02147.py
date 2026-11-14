from pathlib import Path
import unittest
from _ui_sources import main_window_source


class WindowManagement02147Tests(unittest.TestCase):
    def test_window_geometry_manager_persists_by_key(self):
        source = Path("carendmr/ui_qt/window_geometry.py").read_text(encoding="utf-8")
        self.assertIn("windows.local.json", source)
        self.assertIn("saveGeometry()", source)
        self.assertIn("restoreGeometry(raw)", source)
        self.assertIn("ensure_visible", source)

    def test_main_menu_contains_window_management(self):
        source = main_window_source()
        self.assertIn('self.menuBar().addMenu("Fenster")', source)
        self.assertIn('"Alle Fenster nach vorne"', source)
        self.assertIn('"Alle Zusatzfenster schließen"', source)
        self.assertIn('"Fensterpositionen zurücksetzen"', source)

    def test_qrz_uses_shared_geometry_key(self):
        source = main_window_source()
        self.assertIn('self.window_geometry.register("qrz_station", self._qrz_window)', source)

    def test_other_auxiliary_windows_are_registered(self):
        source = main_window_source()
        for key in ("settings", "audio_benchmark", "audio_coach", "audio_tuner"):
            self.assertIn(f'self.window_geometry.register("{key}"', source)

    def test_tg_monitor_persists_geometry_and_accepts_activation(self):
        source = Path("carendmr/tg_monitor/window.py").read_text(encoding="utf-8")
        control = Path("carendmr/tg_monitor/instance_control.py").read_text(encoding="utf-8")
        self.assertIn('register("tg_monitor", window)', source)
        self.assertIn('command == "activate"', source)
        self.assertIn('command == "close"', source)
        self.assertIn("send_tg_monitor_command", control)

    def test_main_window_can_activate_external_monitor(self):
        source = main_window_source()
        self.assertIn('send_tg_monitor_command("activate")', source)
        self.assertIn('send_tg_monitor_command("close")', source)


if __name__ == "__main__":
    unittest.main()
