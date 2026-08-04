import time
import unittest

from carendmr.application import EventService, InformationManager
from carendmr.domain import (
    EventLevel,
    InformationCategory,
    InformationPriority,
    OperatingContext,
)


class CarenAssistFramework0242Tests(unittest.TestCase):
    def test_context_is_attached_to_new_messages(self):
        manager = InformationManager()
        manager.set_context(OperatingContext.OPERATION)
        message = manager.publish("Empfang aktiv.", code="reception.active")
        self.assertEqual(OperatingContext.OPERATION, message.context)

    def test_explicit_context_overrides_current_context(self):
        manager = InformationManager()
        manager.set_context(OperatingContext.OPERATION)
        message = manager.publish(
            "Mikrofon geprüft.",
            context=OperatingContext.AUDIO,
            category=InformationCategory.AUDIO,
        )
        self.assertEqual(OperatingContext.AUDIO, message.context)

    def test_history_supports_last_and_recent(self):
        manager = InformationManager(maximum=3)
        manager.publish("eins", speak=False)
        manager.publish("zwei", speak=True)
        manager.publish("drei", speak=False)
        self.assertEqual("drei", manager.last().short_text)
        self.assertEqual("zwei", manager.last(spoken_only=True).short_text)
        self.assertEqual(["zwei", "drei"], [item.short_text for item in manager.recent(2)])

    def test_visual_speech_and_log_channels_are_independent(self):
        manager = InformationManager()
        visual, speech, log = [], [], []
        manager.subscribe_visual(visual.append)
        manager.subscribe_speech(speech.append)
        manager.subscribe_log(log.append)
        message = manager.publish("Verbunden.", speak=False)
        self.assertEqual([message], visual)
        self.assertEqual([], speech)
        self.assertEqual([message], log)

    def test_diagnostics_record_dispatch_times_and_queue(self):
        manager = InformationManager()

        def slow_visual(_message):
            time.sleep(0.006)

        manager.subscribe_visual(slow_visual)
        manager.publish("Messung")
        stats = manager.diagnostics()
        self.assertEqual(1, stats.events_total)
        self.assertGreaterEqual(stats.maximum_ms, 5.0)
        self.assertGreaterEqual(stats.warning_count, 1)
        self.assertEqual(0, stats.queue_current)
        self.assertGreaterEqual(stats.queue_maximum, 1)
        self.assertEqual(1, len(manager.diagnostic_measurements()))

    def test_event_service_keeps_structured_metadata(self):
        service = EventService()
        received = []
        service.subscribe_information(received.append)
        service.set_context(OperatingContext.SETTINGS)
        service.publish(
            "WAV-Diagnose aktiv.",
            EventLevel.INFO,
            code="settings.wav_debug.enabled",
            long_text="Die WAV-Audiodiagnose ist aktiviert.",
            category=InformationCategory.DIAGNOSTICS,
            priority=InformationPriority.LOW,
            metadata={"enabled": True},
        )
        self.assertEqual(OperatingContext.SETTINGS, received[0].context)
        self.assertEqual(True, received[0].metadata["enabled"])
        self.assertEqual(1, service.diagnostics().events_total)


if __name__ == "__main__":
    unittest.main()
