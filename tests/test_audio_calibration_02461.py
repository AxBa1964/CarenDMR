import tempfile
import unittest
from pathlib import Path
from threading import Event

from carendmr.application.audio_send_service import AudioSendService
from carendmr.audio import AudioDevice
from carendmr.ui.main_window import MainWindow


class MonitorBackend:
    def __init__(self):
        self.called = False

    def query_devices(self):
        return [
            AudioDevice(
                index=0, name="Test Mic", host_api="MME",
                max_input_channels=1, max_output_channels=0,
                default_sample_rate=16000, is_default_input=True,
            ),
            AudioDevice(
                index=1, name="Test Speaker", host_api="MME",
                max_input_channels=0, max_output_channels=2,
                default_sample_rate=48000, is_default_output=True,
            ),
        ]

    def stream_input_blocks_until(self, **kwargs):
        self.called = True
        kwargs["level_callback"](20.0)
        kwargs["level_callback"](40.0)
        kwargs["stop_event"].set()


class AudioCalibration02461Tests(unittest.TestCase):
    def test_talkgroup_validation_accepts_only_digits(self):
        self.assertFalse(MainWindow._validate_talkgroup_input(""))
        self.assertTrue(MainWindow._validate_talkgroup_input("9990"))
        self.assertFalse(MainWindow._validate_talkgroup_input("ABC"))
        self.assertFalse(MainWindow._validate_talkgroup_input("91 "))
        self.assertFalse(MainWindow._validate_talkgroup_input("123456789"))

    def test_local_monitor_applies_current_gain_without_network(self):
        backend = MonitorBackend()
        with tempfile.TemporaryDirectory() as directory:
            service = AudioSendService(Path(directory), backend=backend)
            service.set_gain_percent(50)
            levels = []
            service.monitor_microphone_until(Event(), level_callback=levels.append)
        self.assertTrue(backend.called)
        self.assertEqual([10.0, 20.0], levels)

    def test_ui_exposes_local_microphone_test(self):
        source = (Path(__file__).parents[1] / "carendmr" / "ui" / "main_window.py").read_text(encoding="utf-8")
        self.assertIn('text="Mikrofon testen (10 s)"', source)
        self.assertIn('Lokaler Mikrofontest läuft – keine Funkübertragung.', source)
        self.assertIn('validatecommand=talkgroup_vcmd', source)
        self.assertIn('self._force_stop_transmit(reason="Reiterwechsel")', source)


if __name__ == "__main__":
    unittest.main()
