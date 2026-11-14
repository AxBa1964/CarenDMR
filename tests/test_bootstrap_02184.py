"""Gemeinsamer Funkkern aus carendmr/bootstrap.py (0.2.1.84)."""
import json
import tempfile
import unittest
from pathlib import Path

from carendmr.audio import AudioDevice
from carendmr.bootstrap import RadioCore, build_radio_core

ROOT = Path(__file__).resolve().parents[1]


class FakeAudioBackend:
    """Minimales Audio-Backend ohne echte Geräte."""

    def query_devices(self):
        return [
            AudioDevice(1, "Testmikrofon", "Test API", 1, 0, 48000.0, True, False),
            AudioDevice(2, "Testlautsprecher", "Test API", 0, 2, 48000.0, False, True),
        ]


class BuildRadioCoreTests(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        self.root = Path(self._temp.name)
        (self.root / "config").mkdir()

    def tearDown(self):
        self._temp.cleanup()

    def build(self) -> RadioCore:
        return build_radio_core(self.root, audio_backend=FakeAudioBackend())

    def test_components_share_one_event_bus_and_one_receive_path(self):
        core = self.build()
        self.assertIs(core.receive_service.events, core.events)
        self.assertIs(core.connection_manager.events, core.events)
        self.assertIs(core.connection_manager.receive_service, core.receive_service)
        self.assertIs(core.connection_manager.parrot_service, core.parrot_service)
        self.assertIs(core.controller.connection_manager, core.connection_manager)
        self.assertIs(core.controller.receive_service, core.receive_service)

    def test_parrot_uses_the_same_audio_and_encoder_services(self):
        core = self.build()
        self.assertIs(core.parrot_service.audio_service, core.audio_send_service)
        self.assertIs(core.parrot_service.encoder_service, core.encoder_service)

    def test_saved_audio_settings_are_applied_and_agc_starts_off(self):
        (self.root / "config" / "audio_send.local.json").write_text(
            json.dumps({"output_volume_percent": 150, "output_muted": True, "agc_enabled": True}),
            encoding="utf-8",
        )
        core = self.build()
        self.assertEqual(150, core.audio_send_service.output_volume_percent)
        self.assertEqual(150, core.receive_service._output_volume_percent)
        self.assertTrue(core.receive_service._user_muted.is_set())
        # 0.2.1.45 Diagnose: AGC beim Start bewusst aus, unabhängig von der Speicherung.
        self.assertFalse(core.audio_send_service.agc_enabled)
        self.assertFalse(core.receive_service.agc_enabled)

    def test_each_call_builds_an_independent_core(self):
        first = self.build()
        second = self.build()
        self.assertIsNot(first.receive_service, second.receive_service)
        self.assertIsNot(first.events, second.events)


class WindowsUseSharedCoreTests(unittest.TestCase):
    """Strukturwächter: Oberflächen dürfen den Funkkern nicht selbst verdrahten."""

    def test_windows_take_the_core_from_bootstrap(self):
        for name in ("main_window.py", "easy_window.py"):
            source = (ROOT / "carendmr" / "ui_qt" / name).read_text(encoding="utf-8")
            with self.subTest(window=name):
                self.assertIn("core or build_radio_core(self.project_root)", source)
                for constructor in (
                    "ReceiveService(", "AudioSendService(", "EncoderService(",
                    "ParrotTestService(", "ConnectionManager(", "OperatingController(",
                ):
                    self.assertNotIn(constructor, source)


if __name__ == "__main__":
    unittest.main()
