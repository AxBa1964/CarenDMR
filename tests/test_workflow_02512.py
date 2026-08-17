from pathlib import Path
import unittest


class Workflow02512Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (Path(__file__).parents[1] / "carendmr" / "ui" / "main_window.py").read_text(encoding="utf-8")

    def test_separate_new_talkgroup_field(self):
        self.assertIn('self.new_talkgroup_var = tk.StringVar(value="")', self.source)
        self.assertIn('textvariable=self.new_talkgroup_var', self.source)
        self.assertIn('textvariable=self.talkgroup_var', self.source)

    def test_empty_new_talkgroup_reuses_current_value(self):
        self.assertIn('value = proposed or self.talkgroup_var.get().strip()', self.source)

    def test_focus_speech_is_complete_and_atomic(self):
        self.assertIn('text = f"Timeslot {self._spoken_timeslot', self.source)
        self.assertIn('text = f"Rufart {self._spoken_call_type()', self.source)
        self.assertIn('self.caren_assist.say_focus(text)', self.source)

    def test_new_talkgroup_is_cleared_after_connect(self):
        self.assertIn('self.new_talkgroup_var.set("")', self.source)


if __name__ == "__main__":
    unittest.main()
