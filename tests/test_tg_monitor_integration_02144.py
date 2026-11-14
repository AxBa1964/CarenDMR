from pathlib import Path
import unittest
from _ui_sources import main_window_source


class TGMonitorIntegration02144Tests(unittest.TestCase):
    def test_ipc_does_not_treat_wait_for_bytes_written_as_send_failure(self):
        source = Path("carendmr/ipc/channel_control.py").read_text(encoding="utf-8")
        self.assertIn("socket.waitForBytesWritten(min(timeout_ms, 250))", source)
        self.assertNotIn(
            'if not socket.waitForBytesWritten(timeout_ms):\n'
            '        return False, "Kanal konnte nicht an CarenDMR gesendet werden."',
            source,
        )
        self.assertIn("if not socket.waitForReadyRead(timeout_ms):", source)

    def test_main_menu_can_start_tg_monitor(self):
        source = main_window_source()
        self.assertIn('QAction("TG-Monitor starten", self)', source)
        self.assertIn("subprocess.Popen(", source)
        # Ab 0.2.1.88 liefert app_paths den Startbefehl (Exe oder Skript).
        self.assertIn("command = tg_monitor_command(self.project_root)", source)

    def test_main_window_checks_for_existing_monitor(self):
        source = main_window_source()
        self.assertIn("if is_tg_monitor_running():", source)
        self.assertIn("Der TG-Monitor läuft bereits.", source)

    def test_monitor_enforces_single_instance(self):
        source = Path("carendmr/tg_monitor/window.py").read_text(encoding="utf-8")
        control = Path("carendmr/tg_monitor/instance_control.py").read_text(encoding="utf-8")
        self.assertIn("acquire_tg_monitor_instance()", source)
        self.assertIn("TG_MONITOR_INSTANCE_SERVER", control)
        self.assertIn("if is_tg_monitor_running():", control)


if __name__ == "__main__":
    unittest.main()
