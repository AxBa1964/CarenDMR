"""Asynchrone Bedienung des OperatingController (0.2.1.85)."""
import unittest
from threading import Event

from carendmr.application.operating_controller import OperatingController
from carendmr.application.radio_state_machine import RadioState
from carendmr.domain.models import ApplicationState, ConnectionState

WAIT = 2.0


class FakeStore:
    def __init__(self):
        self.listeners = []

    def subscribe(self, listener):
        self.listeners.append(listener)

    def emit(self, connection):
        for listener in self.listeners:
            listener(ApplicationState(connection=connection))


class FakeReceive:
    def __init__(self):
        self.state_store = FakeStore()
        self.is_running = False
        self.wait_calls = []

    def wait(self, timeout):
        self.wait_calls.append(timeout)
        return True


class FakeManager:
    """Nachbildung des ConnectionManager inkl. der realen Zustandsfolge."""

    def __init__(self, receive):
        self.receive = receive
        self.connect_calls = []
        self.disconnect_calls = 0
        self.connect_result = True
        self.connect_error = None
        self.emit_old_session_end = False
        self.tx_started = Event()
        self.tx_kwargs = None

    def connect(self, tg, ts, call_type):
        self.connect_calls.append((tg, ts, call_type))
        if self.emit_old_session_end:
            # Alte Sitzung endet während connect(), wie beim realen Zielwechsel.
            self.receive.state_store.emit(ConnectionState.STOPPING)
            self.receive.state_store.emit(ConnectionState.DISCONNECTED)
        if self.connect_error is not None:
            raise self.connect_error
        self.receive.is_running = True
        return self.connect_result

    def disconnect(self):
        self.disconnect_calls += 1
        self.receive.is_running = False

    def run_parrot_hold_to_talk(self, stop_event, **kwargs):
        self.tx_kwargs = kwargs
        self.tx_started.set()
        if not stop_event.wait(WAIT):
            raise AssertionError("PTT wurde nicht beendet")
        callback = kwargs.get("tx_complete_callback")
        if callback is not None:
            callback()
        return "tx-ok"


class Results:
    def __init__(self):
        self.done = Event()
        self.value = None
        self.error = None

    def on_done(self, value):
        self.value = value
        self.done.set()

    def on_error(self, error):
        self.error = error
        self.done.set()


def make():
    receive = FakeReceive()
    manager = FakeManager(receive)
    return OperatingController(manager, receive), manager, receive


def connected():
    controller, manager, receive = make()
    controller.connect(91, 2, "group")
    receive.state_store.emit(ConnectionState.RECEIVING)
    assert controller.snapshot().state is RadioState.CONNECTED
    return controller, manager, receive


class ConnectAsyncTests(unittest.TestCase):
    def test_connect_async_switches_to_connecting_immediately_and_reports_result(self):
        controller, manager, receive = make()
        results = Results()
        controller.connect_async(91, 2, "group", on_done=results.on_done, on_error=results.on_error)
        self.assertIn(controller.snapshot().state, {RadioState.CONNECTING, RadioState.CONNECTED})
        self.assertTrue(results.done.wait(WAIT))
        self.assertIsNone(results.error)
        self.assertTrue(results.value)
        self.assertEqual([(91, 2, "group")], manager.connect_calls)

    def test_invalid_target_is_rejected_before_any_thread_starts(self):
        controller, manager, _receive = make()
        with self.assertRaises(ValueError):
            controller.connect_async(0, 2, "group")
        self.assertEqual([], manager.connect_calls)
        self.assertIs(RadioState.DISCONNECTED, controller.snapshot().state)

    def test_connect_error_is_reported_and_state_becomes_error(self):
        controller, manager, _receive = make()
        manager.connect_error = RuntimeError("Server nicht erreichbar")
        results = Results()
        controller.connect_async(91, 2, "group", on_done=results.on_done, on_error=results.on_error)
        self.assertTrue(results.done.wait(WAIT))
        self.assertIsInstance(results.error, RuntimeError)
        self.assertIs(RadioState.ERROR, controller.snapshot().state)

    def test_old_session_end_during_connect_is_not_reported_as_disconnected(self):
        controller, manager, receive = make()
        manager.emit_old_session_end = True
        seen = []
        controller.subscribe(lambda snapshot: seen.append(snapshot.state))
        controller.connect(91, 2, "group")
        self.assertNotIn(RadioState.DISCONNECTED, seen)
        self.assertNotIn(RadioState.DISCONNECTING, seen)
        receive.state_store.emit(ConnectionState.RECEIVING)
        self.assertIs(RadioState.CONNECTED, controller.snapshot().state)

    def test_real_disconnect_after_connect_is_still_reported(self):
        controller, _manager, receive = make()
        controller.connect(91, 2, "group")
        receive.state_store.emit(ConnectionState.DISCONNECTED)
        self.assertIs(RadioState.DISCONNECTED, controller.snapshot().state)

    def test_unchanged_target_on_running_receive_becomes_connected(self):
        controller, manager, receive = make()
        receive.is_running = True
        manager.connect_result = False
        self.assertFalse(controller.connect(91, 2, "group"))
        self.assertIs(RadioState.CONNECTED, controller.snapshot().state)


class PttAsyncTests(unittest.TestCase):
    def test_start_ptt_requires_connection(self):
        controller, _manager, _receive = make()
        with self.assertRaises(RuntimeError):
            controller.start_ptt()

    def test_start_and_stop_ptt_pass_callbacks_and_return_to_connected(self):
        controller, manager, _receive = connected()
        results = Results()
        wire_complete = Event()
        levels = []
        controller.start_ptt(
            level_callback=levels.append,
            tx_complete_callback=wire_complete.set,
            on_done=results.on_done,
            on_error=results.on_error,
        )
        self.assertIs(RadioState.TRANSMITTING, controller.snapshot().state)
        self.assertTrue(controller.is_transmitting)
        self.assertTrue(manager.tx_started.wait(WAIT))
        self.assertIs(manager.tx_kwargs["level_callback"].__self__, levels)
        self.assertTrue(manager.tx_kwargs["optimize"])
        self.assertTrue(controller.stop_ptt())
        self.assertTrue(results.done.wait(WAIT))
        self.assertEqual("tx-ok", results.value)
        self.assertTrue(wire_complete.is_set())
        self.assertFalse(controller.is_transmitting)
        self.assertIs(RadioState.CONNECTED, controller.snapshot().state)

    def test_second_ptt_while_transmitting_is_rejected(self):
        controller, manager, _receive = connected()
        controller.start_ptt()
        self.assertTrue(manager.tx_started.wait(WAIT))
        with self.assertRaises(RuntimeError):
            controller.start_ptt()
        controller.stop_ptt()

    def test_stop_ptt_without_transmission_returns_false(self):
        controller, _manager, _receive = connected()
        self.assertFalse(controller.stop_ptt())

    def test_receive_pause_during_tx_does_not_end_transmitting(self):
        controller, manager, receive = connected()
        controller.start_ptt()
        self.assertTrue(manager.tx_started.wait(WAIT))
        receive.state_store.emit(ConnectionState.STOPPING)
        receive.state_store.emit(ConnectionState.DISCONNECTED)
        self.assertIs(RadioState.TRANSMITTING, controller.snapshot().state)
        controller.stop_ptt()


class DisconnectAsyncTests(unittest.TestCase):
    def test_disconnect_async_stops_running_ptt_and_waits_for_receive(self):
        controller, manager, receive = connected()
        tx_results = Results()
        controller.start_ptt(on_done=tx_results.on_done, on_error=tx_results.on_error)
        self.assertTrue(manager.tx_started.wait(WAIT))
        results = Results()
        controller.disconnect_async(wait_timeout=8.0, on_done=results.on_done, on_error=results.on_error)
        self.assertTrue(tx_results.done.wait(WAIT))
        self.assertTrue(results.done.wait(WAIT))
        self.assertIsNone(results.error)
        self.assertTrue(results.value)
        self.assertEqual(1, manager.disconnect_calls)
        self.assertEqual([8.0], receive.wait_calls)

    def test_disconnect_async_marks_disconnecting_immediately(self):
        controller, _manager, _receive = connected()
        done = Results()
        controller.disconnect_async(wait_timeout=None, on_done=done.on_done)
        self.assertIn(
            controller.snapshot().state,
            {RadioState.DISCONNECTING, RadioState.DISCONNECTED},
        )
        self.assertTrue(done.done.wait(WAIT))


if __name__ == "__main__":
    unittest.main()
