import tempfile
import unittest
import wave
from pathlib import Path
from threading import Event

import numpy as np

from carendmr.application.audio_send_service import AudioSendService
from carendmr.audio import AudioDevice


class StreamingBackend:
    def query_devices(self):
        return [
            AudioDevice(0, "Test Mic", "MME", 1, 0, 16000, True, False),
            AudioDevice(1, "Test Speaker", "MME", 0, 2, 48000, False, True),
        ]

    def stream_input_blocks_until(self, **kwargs):
        block = np.full((160, 1), 0.25, dtype=np.float32)
        kwargs["block_callback"](block)
        kwargs["level_callback"](25.0)
        kwargs["stop_event"].set()


class AudioCalibration02462Tests(unittest.TestCase):
    def test_microphone_test_writes_wav_only_with_debug_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            service = AudioSendService(root, backend=StreamingBackend())
            service.microphones()
            path = service.monitor_microphone_until(Event())
            self.assertIsNone(path)
            self.assertFalse((root / "logs" / "audio_debug").exists())

            service.set_audio_debug_wav_enabled(True)
            path = service.monitor_microphone_until(Event())
            self.assertIsNotNone(path)
            self.assertTrue(path.exists())
            self.assertIn("gain_100", path.name)
            with wave.open(str(path), "rb") as wav_file:
                self.assertEqual(1, wav_file.getnchannels())
                self.assertEqual(16000, wav_file.getframerate())
                self.assertGreater(wav_file.getnframes(), 0)

    def test_gain_range_is_zero_to_one_hundred(self):
        with tempfile.TemporaryDirectory() as directory:
            service = AudioSendService(Path(directory), backend=StreamingBackend())
            self.assertEqual(0, service.set_gain_percent(0))
            self.assertEqual(100, service.set_gain_percent(100))
            with self.assertRaises(ValueError):
                service.set_gain_percent(101)


if __name__ == "__main__":
    unittest.main()
