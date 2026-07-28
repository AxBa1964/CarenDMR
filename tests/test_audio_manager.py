import json
import tempfile
import unittest
from pathlib import Path

from carendmr.audio import (
    AudioDevice,
    AudioDirection,
    AudioManager,
    AudioSelection,
    AudioUnavailableError,
)


class FakeBackend:
    def __init__(self, devices):
        self.devices = list(devices)
        self.calls = []

    def query_devices(self):
        return list(self.devices)

    def record_and_play(self, **kwargs):
        self.calls.append(kwargs)


def device(
    index,
    name,
    *,
    input_channels=0,
    output_channels=0,
    default_input=False,
    default_output=False,
):
    return AudioDevice(
        index=index,
        name=name,
        host_api="Windows WASAPI",
        max_input_channels=input_channels,
        max_output_channels=output_channels,
        default_sample_rate=48000.0,
        is_default_input=default_input,
        is_default_output=default_output,
    )


class AudioManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.config = Path(self.temp.name) / "audio.local.json"

    def tearDown(self):
        self.temp.cleanup()

    def test_scan_separates_input_and_output(self):
        manager = AudioManager(
            FakeBackend([
                device(0, "Mic", input_channels=1),
                device(1, "Speaker", output_channels=2),
                device(2, "Headset", input_channels=1, output_channels=2),
            ]),
            self.config,
        )
        manager.scan()

        self.assertEqual(
            ["Mic", "Headset"],
            [d.name for d in manager.list_devices(AudioDirection.INPUT)],
        )
        self.assertEqual(
            ["Speaker", "Headset"],
            [d.name for d in manager.list_devices(AudioDirection.OUTPUT)],
        )

    def test_selection_is_found_without_using_old_index(self):
        backend = FakeBackend([
            device(7, "Jabra Speak 510", input_channels=1),
        ])
        manager = AudioManager(backend, self.config)
        manager.scan()
        selection = AudioSelection(
            name="Jabra Speak 510",
            host_api="Windows WASAPI",
            direction=AudioDirection.INPUT,
        )

        found = manager.find_selection(selection)

        self.assertIsNotNone(found)
        self.assertEqual(7, found.index)

    def test_missing_saved_device_falls_back_to_default(self):
        self.config.write_text(
            json.dumps({
                "input": {
                    "name": "Nicht angeschlossen",
                    "host_api": "Windows WASAPI",
                    "direction": "input",
                }
            }),
            encoding="utf-8",
        )
        manager = AudioManager(
            FakeBackend([
                device(
                    3,
                    "Standardmikrofon",
                    input_channels=1,
                    default_input=True,
                )
            ]),
            self.config,
        )
        manager.scan()

        result = manager.resolve(AudioDirection.INPUT)

        self.assertTrue(result.used_fallback)
        self.assertEqual("Standardmikrofon", result.device.name)
        self.assertIn("nicht verfügbar", result.message)

    def test_no_input_device_has_actionable_error(self):
        manager = AudioManager(
            FakeBackend([device(0, "Speaker", output_channels=2)]),
            self.config,
        )
        manager.scan()

        with self.assertRaisesRegex(
            AudioUnavailableError,
            "Bitte schließen Sie",
        ):
            manager.resolve(AudioDirection.INPUT)

    def test_save_selection_does_not_store_device_index(self):
        mic = device(11, "Mic", input_channels=1)
        speaker = device(12, "Speaker", output_channels=2)
        manager = AudioManager(FakeBackend([mic, speaker]), self.config)

        manager.save_selection(mic, speaker)

        raw = json.loads(self.config.read_text(encoding="utf-8"))
        self.assertNotIn("index", raw["input"])
        self.assertEqual("Mic", raw["input"]["name"])

    def test_loopback_uses_resolved_devices(self):
        mic = device(
            4,
            "Mic",
            input_channels=1,
            default_input=True,
        )
        speaker = device(
            8,
            "Speaker",
            output_channels=2,
            default_output=True,
        )
        backend = FakeBackend([mic, speaker])
        manager = AudioManager(backend, self.config)

        manager.run_loopback_test(duration_seconds=2.0)

        self.assertEqual(1, len(backend.calls))
        self.assertEqual(4, backend.calls[0]["input_index"])
        self.assertEqual(8, backend.calls[0]["output_index"])
        self.assertEqual(2.0, backend.calls[0]["duration_seconds"])


if __name__ == "__main__":
    unittest.main()
