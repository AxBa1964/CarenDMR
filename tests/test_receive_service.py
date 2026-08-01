import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from carendmr.application import ReceiveService
from carendmr.brandmeister.listen import LiveCallActivity, LiveListenProgress, LiveListenResult
from carendmr.domain import ConnectionState


class ReceiveServiceTests(unittest.TestCase):
    def test_service_bridges_receive_technology_to_application_state(self):
        captured = {}

        def fake_listen(_config, **kwargs):
            captured.update(kwargs)
            time.sleep(0.05)
            kwargs["call_activity_callback"](
                LiveCallActivity(True, 2_632_198, 91, 2, 77)
            )
            kwargs["progress_callback"](
                LiveListenProgress(2.0, 5, 3, 9, 0, 0, 0, 0)
            )
            kwargs["call_activity_callback"](
                LiveCallActivity(False, 2_632_198, 91, 2, 77)
            )
            return LiveListenResult(
                True, True, 1440, 2.0, 5, 3, 9, 1440,
                0, 0, 0, 0, False, True,
            )

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "config").mkdir()
            with patch(
                "carendmr.application.receive_service.BrandMeisterConfigStore.load",
                return_value=type("Config", (), {"host": "server", "port": 62031})(),
            ):
                service = ReceiveService(root, listen_function=fake_listen)
                self.assertTrue(service.start())
                self.assertFalse(service.start())
                self.assertTrue(service.wait(2.0))

        state = service.state_store.get()
        self.assertEqual(ConnectionState.DISCONNECTED, state.connection)
        self.assertFalse(state.brandmeister_connected)
        self.assertFalse(state.receive_active)
        self.assertEqual(3, state.statistics.voice_bursts)
        messages = [event.message for event in service.events.snapshot()]
        self.assertEqual(1, messages.count("Anmeldung bei BrandMeister erfolgreich."))
        self.assertEqual(1, messages.count("Empfang auf Talkgroup 91, Timeslot 2 gestartet."))
        self.assertIn("DMR-ID 2632198 spricht auf Talkgroup 91, Timeslot 2.", messages)
        self.assertTrue(any("Sprechdurchgang von DMR-ID 2632198 beendet" in message for message in messages))
        self.assertIn("stop_requested", captured)
        self.assertFalse(captured["stop_requested"]())

    def test_stop_sets_cooperative_cancel_signal(self):
        def fake_listen(_config, **kwargs):
            while not kwargs["stop_requested"]():
                time.sleep(0.005)
            return LiveListenResult(
                True, True, 0, 0.1, 0, 0, 0, 0,
                0, 0, 0, 0, False, True,
            )

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "config").mkdir()
            with patch(
                "carendmr.application.receive_service.BrandMeisterConfigStore.load",
                return_value=type("Config", (), {"host": "server", "port": 62031})(),
            ):
                service = ReceiveService(root, listen_function=fake_listen)
                service.start()
                time.sleep(0.02)
                service.stop()
                self.assertTrue(service.wait(2.0))
        self.assertEqual(ConnectionState.DISCONNECTED, service.state_store.get().connection)


if __name__ == "__main__":
    unittest.main()
