import unittest
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock

from carendmr.ui.main_window import MainWindow


class HoldToTalkUiTests(unittest.TestCase):
    def test_release_sets_stop_event_immediately(self):
        window = MainWindow.__new__(MainWindow)
        window._tx_active = True
        window._tx_stop_event = Event()
        window._tx_recording = True
        window._tx_pointer_grabbed = False
        window.parrot_button = Mock()
        window.parrot_status_var = Mock()

        result = MainWindow._release_hold_to_talk(window, SimpleNamespace())

        self.assertEqual("break", result)
        self.assertTrue(window._tx_stop_event.is_set())
        self.assertFalse(window._tx_recording)
        call = window.parrot_button.configure.call_args.kwargs
        self.assertEqual(call["text"], "TX NICHT VERFÜGBAR\nEmpfang wird vorbereitet")
        self.assertEqual(call["state"], "disabled")

    def test_timer_does_not_overwrite_processing_status_after_release(self):
        window = MainWindow.__new__(MainWindow)
        window._tx_active = True
        window._tx_recording = False
        window._tx_started_at = 0.0
        window._tx_stop_event = Event()
        window.parrot_status_var = Mock()
        window.root = Mock()
        window.audio_send_service = SimpleNamespace(tx_safety_limit_seconds=15)

        MainWindow._update_tx_timer(window)

        window.parrot_status_var.set.assert_not_called()
        window.root.after.assert_not_called()


    def test_force_stop_transmit_releases_active_tx(self):
        window = MainWindow.__new__(MainWindow)
        window._tx_active = True
        window._tx_announce_pending = False
        window._tx_stop_event = Event()
        window._tx_recording = True
        window._tx_pointer_grabbed = False
        window.parrot_button = Mock()
        window.parrot_status_var = Mock()
        window.events = Mock()

        MainWindow._force_stop_transmit(window, reason="Reiterwechsel")

        self.assertTrue(window._tx_stop_event.is_set())
        self.assertFalse(window._tx_recording)
        window.events.publish.assert_called()

    def test_tx_button_is_reenabled_when_transmit_really_starts(self):
        source = Path(MainWindow.__module__.replace(".", "/") + ".py")
        project_root = Path(__file__).resolve().parents[1]
        text = (project_root / source).read_text(encoding="utf-8")
        self.assertIn('text="TX EIN\\nSenden aktiv"', text)
        self.assertIn('state="normal"', text)
        self.assertIn('self._force_stop_transmit(reason="Reiterwechsel")', text)
        self.assertIn('widget.configure(**focus_options(active))', text)

    def test_legacy_audio_test_buttons_are_removed(self):
        source = Path(MainWindow.__module__.replace(".", "/") + ".py")
        project_root = Path(__file__).resolve().parents[1]
        text = (project_root / source).read_text(encoding="utf-8")
        self.assertNotIn("5 Sekunden Testaufnahme", text)
        self.assertNotIn("Testaufnahme wiedergeben", text)
        self.assertNotIn("4 Sekunden Loopback", text)
        self.assertIn('self.root.bind("<ButtonRelease-1>"', text)


if __name__ == "__main__":
    unittest.main()
