import array
import tempfile
import unittest
import wave
from pathlib import Path


class RxAudioDebugWavTest(unittest.TestCase):
    def test_pcm16_wav_format_is_compatible_with_expected_parrot_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "rx_test.wav"
            samples = array.array("h", [0, 1200, -1200, 300])
            with wave.open(str(target), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(8000)
                wav_file.writeframes(samples.tobytes())
            with wave.open(str(target), "rb") as wav_file:
                self.assertEqual(1, wav_file.getnchannels())
                self.assertEqual(2, wav_file.getsampwidth())
                self.assertEqual(8000, wav_file.getframerate())
                self.assertEqual(4, wav_file.getnframes())


if __name__ == "__main__":
    unittest.main()
