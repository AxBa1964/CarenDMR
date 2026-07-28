import json
import tempfile
import unittest
from pathlib import Path

from carendmr.config import ConfigError, load_config


class ConfigTests(unittest.TestCase):
    def test_valid_config_is_loaded(self):
        data = {
            "dmr": {"default_talkgroup": 91},
            "logging": {"directory": "logs"},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.json"
            path.write_text(json.dumps(data), encoding="utf-8")

            config = load_config(path)

        self.assertEqual(91, config["dmr"]["default_talkgroup"])

    def test_missing_file_raises_config_error(self):
        with self.assertRaises(ConfigError):
            load_config(Path("does-not-exist.json"))

    def test_invalid_talkgroup_raises_config_error(self):
        data = {
            "dmr": {"default_talkgroup": 0},
            "logging": {"directory": "logs"},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.json"
            path.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaises(ConfigError):
                load_config(path)


if __name__ == "__main__":
    unittest.main()
