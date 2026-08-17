import tempfile
import unittest
from pathlib import Path

import numpy as np

from carendmr.application import AudioSendService
from carendmr.audio import AudioDevice


class FakeCaptureBackend:
    def __init__(self):
        self.devices = [
            AudioDevice(1, "Testmikrofon", "Test API", 1, 0, 48000.0, True, False),
            AudioDevice(2, "Testlautsprecher", "Test API", 0, 2, 48000.0, False, True),
        ]
        self.record_calls = []
        self.play_calls = []
        self.loopback_calls = []

    def query_devices(self):
        return list(self.devices)

    def record_input(self, **kwargs):
        self.record_calls.append(kwargs)
        callback = kwargs.get("level_callback")
        if callback:
            callback(37.0)
            callback(64.0)
        frames = int(kwargs["duration_seconds"] * kwargs["sample_rate"])
        return np.zeros((frames, kwargs["channels"]), dtype=np.float32)

    def play_samples(self, samples, **kwargs):
        self.play_calls.append((samples, kwargs))

    def record_and_play(self, **kwargs):
        self.loopback_calls.append(kwargs)


class AudioSendServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.backend = FakeCaptureBackend()
        self.mute_events = []
        self.service = AudioSendService(
            self.root, backend=self.backend,
            mute_receive=lambda: self.mute_events.append("mute"),
            unmute_receive=lambda: self.mute_events.append("unmute"),
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_microphones_resolves_default_input(self):
        devices = self.service.microphones()
        self.assertEqual(["Testmikrofon"], [device.name for device in devices])
        self.assertEqual("Testmikrofon", self.service.selected_input.name)

    def test_recording_uses_16khz_mono_and_reports_peak(self):
        levels = []
        result = self.service.record_test(duration_seconds=2.0, level_callback=levels.append)
        self.assertEqual(16000, self.backend.record_calls[0]["sample_rate"])
        self.assertEqual(1, self.backend.record_calls[0]["channels"])
        self.assertEqual(32000, result.captured_samples)
        self.assertEqual(64.0, result.peak_percent)
        self.assertEqual([37.0, 64.0], levels)

    def test_playback_requires_recording(self):
        with self.assertRaisesRegex(RuntimeError, "keine Testaufnahme"):
            self.service.play_test()

    def test_playback_uses_default_output(self):
        self.service.record_test(duration_seconds=1.0)
        self.mute_events.clear()
        self.service.play_test()
        self.assertEqual(2, self.backend.play_calls[0][1]["output_index"])
        self.assertEqual(16000, self.backend.play_calls[0][1]["sample_rate"])
        self.assertEqual(["mute", "unmute"], self.mute_events)

    def test_loopback_is_local_and_uses_16khz(self):
        self.service.run_loopback(duration_seconds=3.0)
        self.assertEqual(3.0, self.backend.loopback_calls[0]["duration_seconds"])
        self.assertEqual(16000, self.backend.loopback_calls[0]["sample_rate"])

    def test_recording_mutes_and_restores_receive_audio(self):
        self.service.record_test(duration_seconds=0.1)
        self.assertEqual(["mute", "unmute"], self.mute_events)

    def test_loopback_mutes_and_restores_receive_audio(self):
        self.service.run_loopback(duration_seconds=0.1)
        self.assertEqual(["mute", "unmute"], self.mute_events)

    def test_gain_is_limited_to_one_hundred_percent_and_persisted(self):
        self.service.set_gain_percent(100)
        self.service.save_settings()
        self.backend.record_input = lambda **kwargs: np.array([[0.75], [-0.75]], dtype=np.float32)
        result = self.service.record_test(duration_seconds=0.1)
        self.assertEqual(100, result.gain_percent)
        np.testing.assert_allclose(self.service._recording[:, 0], [0.75, -0.75])
        reloaded = AudioSendService(self.root, backend=self.backend)
        self.assertEqual(100, reloaded.gain_percent)
        with self.assertRaisesRegex(ValueError, "zwischen 0 und 100"):
            self.service.set_gain_percent(101)

    def test_receive_audio_is_restored_after_recording_error(self):
        def fail(**kwargs):
            raise RuntimeError("capture failed")
        self.backend.record_input = fail
        with self.assertRaisesRegex(RuntimeError, "capture failed"):
            self.service.record_test(duration_seconds=0.1)
        self.assertEqual(["mute", "unmute"], self.mute_events)

    def test_output_volume_and_mute_are_persisted(self):
        self.service.set_output_volume_percent(35)
        self.service.set_user_muted(True)
        self.service.save_settings()
        reloaded = AudioSendService(self.root, backend=self.backend)
        self.assertEqual(35, reloaded.output_volume_percent)
        self.assertTrue(reloaded.user_muted)

    def test_output_volume_supports_four_hundred_percent_and_agc_persists(self):
        self.service.set_output_volume_percent(400)
        self.service.set_agc_enabled(False)
        self.service.save_settings()
        reloaded = AudioSendService(self.root, backend=self.backend)
        self.assertEqual(400, reloaded.output_volume_percent)
        self.assertFalse(reloaded.agc_enabled)

    def test_gain_change_does_not_write_until_save(self):
        self.service.set_gain_percent(75)
        self.assertFalse((self.root / "config" / "audio_send.local.json").exists())
        self.service.save_settings()
        self.assertTrue((self.root / "config" / "audio_send.local.json").exists())

    def test_tx_safety_limit_is_validated_and_persisted(self):
        self.service.set_tx_safety_limit_seconds(120)
        self.service.save_settings()
        reloaded = AudioSendService(self.root, backend=self.backend)
        self.assertEqual(120, reloaded.tx_safety_limit_seconds)
        with self.assertRaisesRegex(ValueError, "zwischen 5 und 300"):
            self.service.set_tx_safety_limit_seconds(4)
        with self.assertRaisesRegex(ValueError, "zwischen 5 und 300"):
            self.service.set_tx_safety_limit_seconds(301)


if __name__ == "__main__":
    unittest.main()

class HoldCaptureBackend(FakeCaptureBackend):
    def record_input_until(self, **kwargs):
        self.record_calls.append(kwargs)
        callback = kwargs.get("level_callback")
        if callback:
            callback(50.0)
        frames = int(2.0 * kwargs["sample_rate"])
        return np.full((frames, kwargs["channels"]), 0.1, dtype=np.float32)


class HoldToTalkAudioTests(unittest.TestCase):
    def test_hold_capture_returns_duration_and_optimizer_diagnostics(self):
        import threading
        with tempfile.TemporaryDirectory() as tmp:
            backend = HoldCaptureBackend()
            service = AudioSendService(Path(tmp), backend=backend)
            service.microphones()
            pcm, duration, hit_limit, diagnostics = service.capture_transmit_pcm_until(
                threading.Event(), max_duration_seconds=15.0, optimize=True
            )
            self.assertEqual(16000, len(pcm))
            self.assertAlmostEqual(2.0, duration)
            self.assertFalse(hit_limit)
            self.assertIsNotNone(diagnostics)
