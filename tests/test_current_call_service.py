import unittest

from carendmr.application import ApplicationStateStore, CurrentCallService, EventService
from carendmr.domain import RadioContact


class FakeClock:
    def __init__(self):
        self.value = 100.0

    def __call__(self):
        return self.value


class CurrentCallServiceTests(unittest.TestCase):
    def test_start_duration_and_finish_are_published(self):
        state = ApplicationStateStore()
        events = EventService()
        clock = FakeClock()
        service = CurrentCallService(state, events, clock=clock)

        service.start(source_id=2_632_198, talkgroup=91, timeslot=2, stream_id=42)
        self.assertEqual(2_632_198, state.get().current_call.source_id)

        clock.value = 114.4
        updated = service.update_duration()
        self.assertAlmostEqual(14.4, updated.elapsed_seconds)

        finished = service.finish()
        self.assertEqual(2_632_198, finished.source_id)
        self.assertIsNone(state.get().current_call)
        messages = [event.message for event in events.snapshot()]
        self.assertIn("DMR-ID 2632198 spricht auf Talkgroup 91, Timeslot 2.", messages)
        self.assertIn("Sprechdurchgang von DMR-ID 2632198 beendet (14 Sekunden).", messages)

    def test_same_stream_does_not_publish_duplicate_start(self):
        state = ApplicationStateStore()
        events = EventService()
        service = CurrentCallService(state, events, clock=lambda: 1.0)
        service.start(source_id=123, talkgroup=91, timeslot=2, stream_id=9)
        service.start(source_id=123, talkgroup=91, timeslot=2, stream_id=9)
        starts = [event for event in events.snapshot() if "spricht auf" in event.message]
        self.assertEqual(1, len(starts))

    def test_speaker_change_finishes_previous_call(self):
        state = ApplicationStateStore()
        events = EventService()
        clock = FakeClock()
        service = CurrentCallService(state, events, clock=clock)
        service.start(source_id=111, talkgroup=91, timeslot=2, stream_id=1)
        clock.value = 103.0
        service.start(source_id=222, talkgroup=91, timeslot=2, stream_id=2)
        self.assertEqual(222, state.get().current_call.source_id)
        messages = [event.message for event in events.snapshot()]
        self.assertIn("Sprechdurchgang von DMR-ID 111 beendet (3 Sekunden).", messages)

    def test_contact_lookup_enriches_call_and_event(self):
        state = ApplicationStateStore()
        events = EventService()
        contact = RadioContact(2632198, "DO1DPL", "Axel", "Baruschke", country="Germany")
        service = CurrentCallService(
            state, events, clock=lambda: 1.0, contact_lookup=lambda dmr_id: contact
        )
        call = service.start(source_id=2632198, talkgroup=91, timeslot=2, stream_id=7)
        self.assertEqual("DO1DPL", call.contact.callsign)
        self.assertIn("DO1DPL (Axel Baruschke) spricht", events.snapshot()[-1].message)


if __name__ == "__main__":
    unittest.main()
