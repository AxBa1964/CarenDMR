import unittest

from carendmr.accessibility import ParrotTestAnnouncer, ParrotTestPhase


class RecordingOutput:
    def __init__(self):
        self.messages = []

    def speak(self, text):
        self.messages.append(text)


class ParrotAccessibilityTests(unittest.TestCase):
    def test_all_phases_have_local_non_sensitive_announcements(self):
        output = RecordingOutput()
        announcer = ParrotTestAnnouncer(output)
        for phase in ParrotTestPhase:
            announcer.announce(phase)

        self.assertEqual(6, len(output.messages))
        combined = " ".join(output.messages)
        self.assertIn("beginnt", output.messages[0])
        self.assertIn("Stumme Testübertragung", output.messages[1])
        self.assertIn("keine Sprache", output.messages[1])
        self.assertIn("Echo", output.messages[2])
        self.assertIn("erfolgreich", output.messages[3])
        self.assertIn("keine Wiederholung", output.messages[4])
        self.assertIn("Zeitlimits", output.messages[5])
        self.assertNotIn("9990", combined)
        self.assertNotIn("DMR-ID", combined)
        self.assertNotIn("Rufzeichen", combined)

    def test_announcements_can_be_disabled_without_changing_test_profile(self):
        output = RecordingOutput()
        announcer = ParrotTestAnnouncer(output, enabled=False)
        announcer.announce(ParrotTestPhase.START)
        self.assertEqual([], output.messages)

    def test_unknown_phase_fails_clearly(self):
        with self.assertRaisesRegex(TypeError, "ungültig"):
            ParrotTestAnnouncer(RecordingOutput()).announce("echo")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
