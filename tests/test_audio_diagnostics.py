import tempfile
import unittest
from pathlib import Path

from carendmr.audio import AudioDevice, AudioManager
from carendmr.diagnostics import AudioDiagnostics, DiagnosticStatus


class FakeBackend:
    def __init__(self, devices=None, error=None):
        self.devices = devices or []
        self.error = error

    def query_devices(self):
        if self.error:
            raise self.error
        return list(self.devices)

    def record_and_play(self, **kwargs):
        pass


class AudioDiagnosticsTests(unittest.TestCase):
    def test_reports_missing_input_and_output(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = AudioManager(
                FakeBackend([]),
                Path(directory) / "audio.local.json",
            )

            results = AudioDiagnostics(manager).run()

            self.assertEqual(2, len(results))
            self.assertTrue(
                all(r.status is DiagnosticStatus.ERROR for r in results)
            )
            self.assertTrue(all(r.action for r in results))

    def test_reports_backend_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = AudioManager(
                FakeBackend(error=RuntimeError("PortAudio fehlt.")),
                Path(directory) / "audio.local.json",
            )

            results = AudioDiagnostics(manager).run()

            self.assertEqual(1, len(results))
            self.assertEqual(DiagnosticStatus.ERROR, results[0].status)
            self.assertIn("PortAudio fehlt", results[0].spoken_text())

    def test_available_defaults_produce_warnings_until_saved(self):
        devices = [
            AudioDevice(
                index=0,
                name="Mic",
                host_api="WASAPI",
                max_input_channels=1,
                max_output_channels=0,
                default_sample_rate=48000,
                is_default_input=True,
            ),
            AudioDevice(
                index=1,
                name="Speaker",
                host_api="WASAPI",
                max_input_channels=0,
                max_output_channels=2,
                default_sample_rate=48000,
                is_default_output=True,
            ),
        ]
        with tempfile.TemporaryDirectory() as directory:
            manager = AudioManager(
                FakeBackend(devices),
                Path(directory) / "audio.local.json",
            )

            results = AudioDiagnostics(manager).run()

            self.assertEqual(
                [DiagnosticStatus.WARNING, DiagnosticStatus.WARNING],
                [r.status for r in results],
            )


if __name__ == "__main__":
    unittest.main()
