from __future__ import annotations

import unittest
from threading import Event

from carendmr.application.connection_manager import ConnectionManager


class _Events:
    def __init__(self):
        self.messages = []

    def publish(self, message, level=None):
        self.messages.append((message, level))


class _Receive:
    def __init__(self, running=True):
        self.is_running = running
        self.is_switching = False
        self.target_talkgroup = 91
        self.target_timeslot = 2
        self.events = _Events()
        self.calls = []

    def stop(self):
        self.calls.append("stop")
        self.is_running = False

    def wait(self, timeout):
        self.calls.append(("wait", timeout))
        return True

    def set_receive_target(self, talkgroup, timeslot):
        self.calls.append(("target", talkgroup, timeslot))
        self.target_talkgroup = talkgroup
        self.target_timeslot = timeslot

    def start(self):
        self.calls.append("start")
        self.is_running = True
        return True

    def switch_receive_target(self, talkgroup, timeslot):
        self.calls.append(("switch", talkgroup, timeslot))
        return True


class _Parrot:
    def __init__(self, error=None):
        self.error = error

    def run_hold_to_talk(self, stop_event, **kwargs):
        if self.error:
            raise self.error
        return "ok"


class ConnectionManagerTests(unittest.TestCase):
    def test_parrot_restores_previously_running_receive(self):
        receive = _Receive(running=True)
        manager = ConnectionManager(receive, _Parrot(), events=receive.events)

        result = manager.run_parrot_hold_to_talk(Event())

        self.assertEqual(result, "ok")
        self.assertEqual(
            receive.calls,
            ["stop", ("wait", 8.0), ("target", 91, 2), "start"],
        )
        self.assertTrue(receive.is_running)

    def test_parrot_restores_receive_even_after_error(self):
        receive = _Receive(running=True)
        manager = ConnectionManager(receive, _Parrot(RuntimeError("tx failed")), events=receive.events)

        with self.assertRaisesRegex(RuntimeError, "tx failed"):
            manager.run_parrot_hold_to_talk(Event())

        self.assertTrue(receive.is_running)
        self.assertIn("start", receive.calls)

    def test_parrot_does_not_start_receive_when_it_was_disconnected(self):
        receive = _Receive(running=False)
        manager = ConnectionManager(receive, _Parrot(), events=receive.events)

        manager.run_parrot_hold_to_talk(Event())

        self.assertEqual(receive.calls, [])

    def test_switch_is_delegated(self):
        receive = _Receive(running=True)
        manager = ConnectionManager(receive, _Parrot(), events=receive.events)

        self.assertTrue(manager.switch_receive_target(262, 1))
        self.assertIn(("switch", 262, 1), receive.calls)


if __name__ == "__main__":
    unittest.main()
