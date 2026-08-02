import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from carendmr.application.encoder_service import EncoderService
from carendmr.encoder import (
    AMBE_BYTES_PER_FRAME,
    PCM_SAMPLES_PER_FRAME,
    EncoderSettingsStore,
    EncoderUnavailableError,
    UsbAmbeEncoder,
    default_bridge_path,
)


class EncoderTests(unittest.TestCase):
    def test_settings_store_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = EncoderSettingsStore(root / "encoder.local.json")
            self.assertIsNone(store.load_plugin_path())
            plugin = root / "vocoder_plugin.test"
            plugin.write_bytes(b"test")
            store.save_plugin_path(plugin)
            self.assertEqual(plugin.resolve(), store.load_plugin_path().resolve())
            payload = json.loads((root / "encoder.local.json").read_text())
            self.assertEqual(str(plugin.resolve()), payload["droidstar_plugin_path"])

    def test_default_bridge_names_are_platform_specific(self):
        path = default_bridge_path(Path("/tmp/project"))
        self.assertIn("vocoder_bridge", path.name)

    def test_usb_backend_is_explicitly_unavailable(self):
        with self.assertRaises(EncoderUnavailableError):
            UsbAmbeEncoder()

    def test_plugin_requires_built_bridge(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plugin = root / "plugin"
            plugin.write_bytes(b"not a library")
            service = EncoderService(root)
            with self.assertRaises(EncoderUnavailableError):
                service.configure_and_verify(plugin)

    def test_constants_match_droidstar_frame_contract(self):
        self.assertEqual(160, PCM_SAMPLES_PER_FRAME)
        self.assertEqual(9, AMBE_BYTES_PER_FRAME)


if __name__ == "__main__":
    unittest.main()


class VocoderBridgeSourceTests(unittest.TestCase):
    def test_bridge_supports_real_destroy_export_and_legacy_typo(self):
        root = Path(__file__).resolve().parent.parent
        source = (root / "native" / "vocoder_plugin_bridge.cpp").read_text(encoding="utf-8")
        self.assertIn('GetProcAddress(handle->library, "destroy")', source)
        self.assertIn('GetProcAddress(handle->library, "destry")', source)
        self.assertIn("create=", source)
        self.assertIn("destroy/destry=", source)

    def test_windows_bridge_build_is_self_contained(self):
        root = Path(__file__).resolve().parent.parent
        script = (root / "native" / "build_vocoder_bridge_windows.ps1").read_text(encoding="utf-8")
        self.assertIn("-static", script)
        self.assertIn("libwinpthread-1.dll", script)
