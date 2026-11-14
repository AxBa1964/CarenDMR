"""Hauptfenster über den OperatingController (0.2.1.86)."""
import unittest
from pathlib import Path
from threading import Event

from carendmr.application.operating_controller import OperatingController
from carendmr.application.radio_state_machine import RadioState
from carendmr.domain.models import ApplicationState, ConnectionState

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "carendmr" / "ui_qt" / "main_window.py").read_text(encoding="utf-8")
WAIT = 2.0


class MainWindowUsesControllerTests(unittest.TestCase):
    """Strukturwächter: Das Hauptfenster führt keinen eigenen Funkablauf mehr."""

    def test_state_machine_is_the_controllers(self):
        self.assertIn("self.radio_state = self.controller.radio_state", MAIN)
        self.assertNotIn("RadioStateMachine(", MAIN)

    def test_no_direct_radio_calls(self):
        for forbidden in (
            "connection_manager.connect(",
            "connection_manager.disconnect(",
            "run_parrot_hold_to_talk(",
            'name="CarenDMR-Qt-Connect"',
            'name="CarenDMR-Qt-Disconnect"',
            'name="CarenDMR-Qt-TX"',
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, MAIN)

    def test_operations_go_through_controller(self):
        for required in (
            "self.controller.connect_async(",
            "self.controller.disconnect_async(",
            "self.controller.start_ptt(",
            "self.controller.stop_ptt()",
            "self.controller.disconnect(wait_timeout=3.0)",
        ):
            with self.subTest(required=required):
                self.assertIn(required, MAIN)

    def test_window_only_sets_state_after_finished_or_failed_disconnect(self):
        # Verbleibende Zustandsübernahmen des Fensters: nach abgeschlossenem
        # Trennen (damit Schnellwahl/TG-Monitor sofort neu verbinden können)
        # und bei einem Fehler beim Trennen. Alles andere führt der Controller.
        self.assertEqual(2, MAIN.count("self.radio_state.synchronize("))
        self.assertIn("self.radio_state.synchronize(RadioState.DISCONNECTED)", MAIN)
        self.assertIn("self.radio_state.synchronize(RadioState.ERROR)", MAIN)


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

    def wait(self, timeout):
        return True


class FakeManager:
    def __init__(self, receive):
        self.receive = receive
        self.tx_started = Event()
        self.release_tx = Event()

    def connect(self, tg, ts, call_type):
        self.receive.is_running = True
        return True

    def disconnect(self):
        self.receive.is_running = False

    def run_parrot_hold_to_talk(self, stop_event, **kwargs):
        self.tx_started.set()
        stop_event.wait(WAIT)
        # Nach TX läuft der Empfang wieder, bevor das Trennen greift.
        self.release_tx.wait(WAIT)
        return "tx-ok"


class DisconnectDuringTxTests(unittest.TestCase):
    def test_disconnecting_is_kept_when_tx_ends_during_disconnect(self):
        receive = FakeReceive()
        manager = FakeManager(receive)
        controller = OperatingController(manager, receive)
        controller.connect(91, 2, "group")
        receive.state_store.emit(ConnectionState.RECEIVING)
        done = Event()
        controller.start_ptt(on_done=lambda _r: done.set(), on_error=lambda _e: done.set())
        self.assertTrue(manager.tx_started.wait(WAIT))
        controller.disconnect_async(wait_timeout=None, on_done=lambda _r: None)
        self.assertIs(RadioState.DISCONNECTING, controller.snapshot().state)
        receive.is_running = True
        manager.release_tx.set()
        self.assertTrue(done.wait(WAIT))
        # Ohne Schutz würde das TX-Ende hier fälschlich wieder CONNECTED melden.
        self.assertIs(RadioState.DISCONNECTING, controller.snapshot().state)


if __name__ == "__main__":
    unittest.main()
