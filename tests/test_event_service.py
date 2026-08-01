import unittest

from carendmr.application import EventService
from carendmr.domain import EventLevel


class EventServiceTests(unittest.TestCase):
    def test_event_log_is_bounded_and_notifies(self):
        service = EventService(maximum=2)
        received = []
        service.subscribe(received.append)
        service.publish("eins")
        service.publish("zwei", EventLevel.WARNING)
        service.publish("drei")
        self.assertEqual(3, len(received))
        self.assertEqual(("zwei", "drei"), tuple(e.message for e in service.snapshot()))
        self.assertIn("Warnung", received[1].display_text)


if __name__ == "__main__":
    unittest.main()
