from pathlib import Path
import unittest


class OperatingFramework0241Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (Path(__file__).parents[1] / "carendmr" / "ui" / "main_window.py").read_text(encoding="utf-8")

    def test_timeslot_and_call_type_are_direct_buttons(self):
        self.assertIn('for row, value in enumerate(("1", "2"))', self.source)
        self.assertIn('for row, value in enumerate(("Gruppe", "Privat"))', self.source)
        self.assertNotIn('self.timeslot_combo = ttk.Combobox', self.source)
        self.assertNotIn('self.call_type_combo = ttk.Combobox', self.source)

    def test_choice_is_not_indicated_by_colour_only(self):
        self.assertIn('text=f"{value}  AKTIV" if active else value', self.source)
        self.assertIn('**selection_options(active=active, enabled=enabled)', self.source)

    def test_focus_model_and_structured_events_exist(self):
        self.assertIn('def _register_focus(', self.source)
        self.assertIn('control_id="talkgroup"', self.source)
        self.assertIn('code="operation.timeslot.changed"', self.source)
        self.assertIn('code="operation.call_type.changed"', self.source)

    def test_arrow_key_navigation_is_defined(self):
        self.assertIn('button.bind("<Up>"', self.source)
        self.assertIn('button.bind("<Down>"', self.source)


if __name__ == "__main__":
    unittest.main()
