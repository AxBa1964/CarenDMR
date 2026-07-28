import unittest

from carendmr.core.events import Event, EventBus


class SampleEvent(Event):
    pass


class EventBusTests(unittest.TestCase):
    def test_handler_receives_event(self):
        bus = EventBus()
        received = []
        bus.subscribe(SampleEvent, received.append)

        event = SampleEvent()
        bus.publish(event)

        self.assertEqual([event], received)

    def test_duplicate_subscription_is_ignored(self):
        bus = EventBus()
        received = []

        def handler(event):
            received.append(event)

        bus.subscribe(SampleEvent, handler)
        bus.subscribe(SampleEvent, handler)
        bus.publish(SampleEvent())

        self.assertEqual(1, len(received))

    def test_unsubscribe_removes_handler(self):
        bus = EventBus()
        received = []

        def handler(event):
            received.append(event)

        bus.subscribe(SampleEvent, handler)
        bus.unsubscribe(SampleEvent, handler)
        bus.publish(SampleEvent())

        self.assertEqual([], received)


if __name__ == "__main__":
    unittest.main()
