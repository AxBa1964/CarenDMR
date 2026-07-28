import tempfile
import unittest
from pathlib import Path

from carendmr.network import NetworkConfig, NetworkConfigStore


class NetworkConfigTests(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "network.local.json"
            store = NetworkConfigStore(path)
            expected = NetworkConfig(
                host="master.example.net",
                port=62031,
                timeout_seconds=2.5,
                heartbeat_interval_seconds=5.0,
            )

            store.save(expected)

            self.assertEqual(expected, store.load())

    def test_invalid_port_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "UDP-Port"):
            NetworkConfig(host="example.net", port=70000).validate()

    def test_missing_file_has_actionable_message(self):
        with tempfile.TemporaryDirectory() as directory:
            store = NetworkConfigStore(
                Path(directory) / "network.local.json"
            )
            with self.assertRaisesRegex(ValueError, "network.example.json"):
                store.load()


if __name__ == "__main__":
    unittest.main()
