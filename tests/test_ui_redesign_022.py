from pathlib import Path
import tempfile
import unittest

from carendmr.diagnostics.runtime import initialize, is_enabled, set_enabled


class UiRedesign022Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (Path(__file__).parents[1] / "carendmr" / "ui" / "main_window.py").read_text(encoding="utf-8")

    def test_operation_uses_new_radio_dashboard_terms(self):
        self.assertIn('text="TG wechseln"', self.source)
        self.assertIn('text="FUNKSTEUERUNG"', self.source)
        self.assertIn('text="EREIGNISSE"', self.source)
        self.assertIn('text="TX AUS\\nZum Senden drücken"', self.source)

    def test_diagnostics_can_be_switched_off_and_persisted(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertFalse(initialize(root))
            set_enabled(True)
            self.assertTrue(is_enabled())
            self.assertTrue(initialize(root))
            set_enabled(False)
            self.assertFalse(is_enabled())

    def test_diagnostics_setting_is_exposed(self):
        self.assertIn('text="Diagnosemodus aktiv (ausführliche PowerShell-Ausgaben)"', self.source)
        self.assertIn('command=self._on_diagnostics_changed', self.source)

    def test_fixed_dashboard_regions(self):
        self.assertIn('grid_propagate(False)', self.source)
        self.assertIn('text="SYSTEM INFO"', self.source)
        self.assertIn('uniform="main"', self.source)

    def test_custom_navigation_highlights_active_page(self):
        self.assertIn('def _show_page', self.source)
        self.assertIn('font=("Segoe UI", 13 if active else 10, "bold")', self.source)


if __name__ == "__main__":
    unittest.main()
