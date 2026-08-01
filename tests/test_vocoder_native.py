import hashlib
import platform
import shutil
import struct
import subprocess
import unittest
from unittest.mock import patch
from pathlib import Path

from carendmr.vocoder import (
    NativeMbeReceiveVocoder,
    VocoderDecodeError,
    VocoderUnavailableError,
)


from carendmr.vocoder.native import _default_library_path


ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "native"
SILENCE = bytes.fromhex("b9e881526173002a6b")
SILENCE_PCM_SHA256 = {
    "Darwin": "97a2d3481d4fca1eec401e78997820aac176f730a2b2a29ef32c750dc045bb4f",
    "Linux": "964d78ace95a73832ffd62e38062d86ee8dab5bcdf697c97d8bc810644048db7",
}


class NativeLibraryPathTests(unittest.TestCase):
    def test_windows_uses_local_dll(self):
        with patch("carendmr.vocoder.native.platform.system", return_value="Windows"):
            self.assertEqual(_default_library_path().name, "carendmr_mbe.dll")

    def test_macos_uses_dylib(self):
        with patch("carendmr.vocoder.native.platform.system", return_value="Darwin"):
            self.assertEqual(_default_library_path().name, "libcarendmr_mbe.dylib")

    def test_linux_uses_so(self):
        with patch("carendmr.vocoder.native.platform.system", return_value="Linux"):
            self.assertEqual(_default_library_path().name, "libcarendmr_mbe.so")


class NativeMbeReceiveVocoderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if shutil.which("make") is None or shutil.which("cc") is None:
            raise unittest.SkipTest(
                "Ein C-Compiler und make werden für den nativen Test benötigt."
            )
        subprocess.run(
            ["make", "clean"],
            cwd=NATIVE,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["make", "check"],
            cwd=NATIVE,
            check=True,
            capture_output=True,
            text=True,
        )

    def test_three_upstream_silence_vectors_have_deterministic_pcm(self):
        with NativeMbeReceiveVocoder() as decoder:
            frames = [decoder.decode(SILENCE) for _ in range(3)]

        pcm = b"".join(
            struct.pack("<160h", *frame.samples)
            for frame in frames
        )
        self.assertEqual(
            [frame.corrected_errors for frame in frames],
            [0, 0, 0],
        )
        expected_hash = SILENCE_PCM_SHA256.get(platform.system())
        if expected_hash is None:
            self.skipTest("Für diese Plattform ist noch kein PCM-Referenzhash hinterlegt.")
        self.assertEqual(hashlib.sha256(pcm).hexdigest(), expected_hash)

    def test_rejects_invalid_codeword_without_calling_native_decoder(self):
        with NativeMbeReceiveVocoder() as decoder:
            with self.assertRaisesRegex(TypeError, "bytes"):
                decoder.decode(bytearray(9))  # type: ignore[arg-type]
            with self.assertRaisesRegex(ValueError, "9 Bytes"):
                decoder.decode(bytes(8))

    def test_closed_decoder_fails_clearly(self):
        decoder = NativeMbeReceiveVocoder()
        decoder.close()
        decoder.close()
        with self.assertRaisesRegex(VocoderDecodeError, "geschlossen"):
            decoder.decode(SILENCE)

    def test_missing_library_fails_without_exposing_loader_detail(self):
        with self.assertRaisesRegex(VocoderUnavailableError, "nicht verfügbar"):
            NativeMbeReceiveVocoder(NATIVE / "missing.dylib")


if __name__ == "__main__":
    unittest.main()
