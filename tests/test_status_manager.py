import unittest

from carendmr.core.events import EventBus
from carendmr.core.status import AppStatus, StatusChangedEvent, StatusManager


class StatusManagerTests(unittest.TestCase):
    def test_status_change_publishes_event(self):
        bus = EventBus()
        events = []
        bus.subscribe(StatusChangedEvent, events.append)
        manager = StatusManager(bus)

        changed = manager.set_status(AppStatus.READY)

        self.assertTrue(changed)
        self.assertEqual(AppStatus.READY, manager.status)
        self.assertEqual(1, len(events))
        self.assertEqual(AppStatus.STARTING, events[0].previous)
        self.assertEqual(AppStatus.READY, events[0].current)

    def test_unchanged_status_is_not_published_twice(self):
        bus = EventBus()
        events = []
        bus.subscribe(StatusChangedEvent, events.append)
        manager = StatusManager(bus, AppStatus.READY)

        changed = manager.set_status(AppStatus.READY)

        self.assertFalse(changed)
        self.assertEqual([], events)

    def test_changed_detail_is_published(self):
        bus = EventBus()
        events = []
        bus.subscribe(StatusChangedEvent, events.append)
        manager = StatusManager(bus, AppStatus.ERROR)

        manager.set_status(AppStatus.ERROR, "Mikrofon nicht gefunden.")

        self.assertEqual(1, len(events))
        self.assertEqual("Mikrofon nicht gefunden.", events[0].detail)


if __name__ == "__main__":
    unittest.main()
