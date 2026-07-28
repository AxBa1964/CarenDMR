import unittest

from carendmr.accessibility.messages import message_for_status
from carendmr.accessibility.speech import SpeechManager
from carendmr.core.events import EventBus
from carendmr.core.status import AppStatus, StatusManager


class RecordingOutput:
    def __init__(self):
        self.messages = []

    def speak(self, text):
        self.messages.append(text)


class AccessibilityTests(unittest.TestCase):
    def test_status_has_german_message(self):
        self.assertEqual("Verbunden.", message_for_status(AppStatus.CONNECTED))

    def test_detail_is_appended(self):
        self.assertEqual(
            "Ein Fehler ist aufgetreten. Mikrofon nicht gefunden.",
            message_for_status(
                AppStatus.ERROR,
                "Mikrofon nicht gefunden.",
            ),
        )

    def test_speech_manager_reacts_to_status_change(self):
        bus = EventBus()
        output = RecordingOutput()
        speech = SpeechManager(bus, output)
        status = StatusManager(bus)

        speech.start()
        status.set_status(AppStatus.READY)

        self.assertEqual(["CarenDMR ist bereit."], output.messages)

    def test_stop_disables_output(self):
        bus = EventBus()
        output = RecordingOutput()
        speech = SpeechManager(bus, output)
        status = StatusManager(bus)

        speech.start()
        speech.stop()
        status.set_status(AppStatus.READY)

        self.assertEqual([], output.messages)


if __name__ == "__main__":
    unittest.main()
