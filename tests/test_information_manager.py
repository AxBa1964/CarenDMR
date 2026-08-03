import unittest

from carendmr.application import EventService, InformationManager
from carendmr.domain import EventLevel, InformationCategory, InformationPriority


class InformationManagerTests(unittest.TestCase):
    def test_visual_and_speech_channels_receive_same_information(self):
        manager = InformationManager(maximum=3)
        visual = []
        speech = []
        manager.subscribe_visual(visual.append)
        manager.subscribe_speech(speech.append)

        message = manager.publish(
            "Verbunden.",
            code="connection.connected",
            long_text="Mit BrandMeister verbunden. Empfang aktiv.",
            category=InformationCategory.CONNECTION,
            priority=InformationPriority.HIGH,
        )

        self.assertEqual([message], visual)
        self.assertEqual([message], speech)
        self.assertEqual("Mit BrandMeister verbunden. Empfang aktiv.", message.speech_text)

    def test_speech_can_be_suppressed_without_hiding_visual_message(self):
        manager = InformationManager()
        visual = []
        speech = []
        manager.subscribe_visual(visual.append)
        manager.subscribe_speech(speech.append)
        manager.publish("Diagnosewert aktualisiert.", speak=False)
        self.assertEqual(1, len(visual))
        self.assertEqual([], speech)

    def test_action_hint_is_part_of_spoken_guidance(self):
        message = InformationManager().publish(
            "Mikrofon fehlt.",
            long_text="Senden ist nicht möglich. Empfang bleibt aktiv.",
            action_hint="Prüfe die Mikrofonverbindung.",
            level=EventLevel.ERROR,
            category=InformationCategory.ERROR,
            priority=InformationPriority.CRITICAL,
        )
        self.assertIn("Empfang bleibt aktiv", message.speech_text)
        self.assertIn("Prüfe die Mikrofonverbindung", message.speech_text)

    def test_legacy_event_service_remains_compatible(self):
        service = EventService(maximum=2)
        received = []
        service.subscribe(received.append)
        event = service.publish("eins", EventLevel.WARNING, code="test.one")
        self.assertEqual("eins", event.message)
        self.assertEqual("test.one", received[0].code)
        self.assertIn("Warnung", received[0].display_text)


if __name__ == "__main__":
    unittest.main()
