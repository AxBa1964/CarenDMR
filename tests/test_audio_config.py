import tempfile
import unittest
from pathlib import Path

from carendmr.audio.config import AudioConfigStore
from carendmr.audio.devices import AudioDirection, AudioSelection


class AudioConfigStoreTests(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audio.local.json"
            store = AudioConfigStore(path)
            expected = {
                AudioDirection.INPUT: AudioSelection(
                    name="Mikrofon",
                    host_api="WASAPI",
                    direction=AudioDirection.INPUT,
                )
            }

            store.save(expected)
            actual = store.load()

            self.assertEqual(expected, actual)

    def test_missing_file_returns_empty_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            store = AudioConfigStore(Path(directory) / "missing.json")
            self.assertEqual({}, store.load())

    def test_invalid_json_has_clear_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audio.local.json"
            path.write_text("{broken", encoding="utf-8")
            store = AudioConfigStore(path)

            with self.assertRaisesRegex(ValueError, "nicht lesbar"):
                store.load()


if __name__ == "__main__":
    unittest.main()
