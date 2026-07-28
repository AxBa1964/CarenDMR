import unittest

from carendmr.network import HeartbeatController


class HeartbeatControllerTests(unittest.TestCase):
    def test_sends_only_when_interval_is_due(self):
        calls = []
        controller = HeartbeatController(5.0, lambda: calls.append("sent"))

        controller.start(100.0)

        self.assertFalse(controller.tick(104.9))
        self.assertTrue(controller.tick(105.0))
        self.assertEqual(["sent"], calls)
        self.assertFalse(controller.tick(109.9))
        self.assertTrue(controller.tick(110.0))
        self.assertEqual(["sent", "sent"], calls)

    def test_stopped_controller_does_not_send(self):
        calls = []
        controller = HeartbeatController(5.0, lambda: calls.append("sent"))
        controller.start(10.0)
        controller.stop()

        self.assertFalse(controller.tick(20.0))
        self.assertEqual([], calls)

    def test_invalid_interval_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Intervall"):
            HeartbeatController(0, lambda: None)


if __name__ == "__main__":
    unittest.main()
