import tempfile
import unittest
from pathlib import Path
from threading import Event

from carendmr.application.audio_send_service import AudioSendService
from carendmr.audio import AudioDevice


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
    def test_local_monitor_applies_current_gain_without_network(self):
        backend = MonitorBackend()
        with tempfile.TemporaryDirectory() as directory:
            service = AudioSendService(Path(directory), backend=backend)
            service.set_gain_percent(50)
            levels = []
            service.monitor_microphone_until(Event(), level_callback=levels.append)
        self.assertTrue(backend.called)
        self.assertEqual([10.0, 20.0], levels)


if __name__ == "__main__":
    unittest.main()
