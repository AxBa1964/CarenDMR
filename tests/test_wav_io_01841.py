import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from carendmr.diagnostics.wav_io import write_pcm16_mono


class WavIo01841Tests(unittest.TestCase):
    def test_write_pcm16_mono_creates_valid_wav(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audio.wav"
            write_pcm16_mono(path, 8000, b"\x00\x00" * 160)
            with wave.open(str(path), "rb") as wav_file:
                self.assertEqual(wav_file.getnchannels(), 1)
                self.assertEqual(wav_file.getsampwidth(), 2)
                self.assertEqual(wav_file.getframerate(), 8000)
                self.assertEqual(wav_file.getnframes(), 160)

    def test_write_pcm16_mono_does_not_construct_wave_writer_when_raw_open_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "audio.wav"
            calls = []

            def fail_open(self, *args, **kwargs):
                raise PermissionError("blocked")

            with patch.object(Path, "open", fail_open), patch.object(wave, "open", lambda *args, **kwargs: calls.append(args)):
                with self.assertRaises(PermissionError):
                    write_pcm16_mono(target, 8000, b"\x00\x00")
            self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
