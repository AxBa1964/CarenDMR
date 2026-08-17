from pathlib import Path
import unittest


class Workflow0251Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (Path(__file__).parents[1] / "carendmr" / "ui" / "main_window.py").read_text(encoding="utf-8")

    def test_disconnect_waits_for_complete_speech_before_focusing_talkgroup(self):
        self.assertIn('say_and_wait("Verbindung getrennt."', self.source)
        self.assertIn('self.new_talkgroup_var.set("")', self.source)

    def test_connect_mutes_receive_audio_until_assist_is_finished(self):
        self.assertIn('self.receive_service.mute_audio_output()', self.source)
        self.assertIn('self.receive_service.unmute_audio_output()', self.source)

    def test_tab_workflow_uses_active_timeslot_and_call_type(self):
        self.assertIn('self.talkgroup_entry.bind("<Tab>", self._focus_active_timeslot', self.source)
        self.assertIn('button.bind("<Tab>", self._focus_active_call_type', self.source)
        self.assertIn('button.bind("<Tab>", self._focus_connect', self.source)

    def test_only_active_choice_is_in_tab_order(self):
        self.assertGreaterEqual(self.source.count('takefocus=bool(enabled and active)'), 2)


if __name__ == "__main__":
    unittest.main()
