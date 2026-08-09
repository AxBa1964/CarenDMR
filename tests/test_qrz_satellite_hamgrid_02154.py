import json
import tempfile
import unittest
from pathlib import Path

from carendmr.qrz.service import QrzConfig


class QrzSatelliteHamGrid02154Tests(unittest.TestCase):
    def test_qrz_config_reads_optional_maptiler_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "qrz.local.json"
            path.write_text(json.dumps({
                "username": "DO1DPL",
                "password": "secret",
                "own_callsign": "DO1DPL",
                "maptiler_api_key": "abc123",
            }), encoding="utf-8")
            config = QrzConfig.load(path)
            self.assertEqual("abc123", config.maptiler_api_key)

    def test_main_window_passes_maptiler_key_to_qrz_window(self):
        source = Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
        self.assertIn(
            "maptiler_api_key=self.qrz_service.maptiler_api_key",
            source,
        )

    def test_satellite_uses_official_maptiler_satellite_v4(self):
        source = Path("carendmr/ui_qt/qrz_window.py").read_text(encoding="utf-8")
        self.assertIn(
            "https://api.maptiler.com/maps/satellite-v4/",
            source,
        )
        self.assertIn("tileSize: 512", source)
        self.assertIn("zoomOffset: -1", source)
        self.assertIn("&copy; MapTiler", source)
        self.assertIn("setBaseLayer", source)

    def test_satellite_button_is_key_dependent_and_switchable(self):
        source = Path("carendmr/ui_qt/qrz_window.py").read_text(encoding="utf-8")
        self.assertIn("setCheckable(True)", source)
        self.assertIn(
            "self.satellite_button.setEnabled(bool(self.maptiler_api_key))",
            source,
        )
        self.assertIn("def _toggle_satellite", source)
        self.assertIn('mode = "satellite" if enabled else "map"', source)

    def test_ham_grid_is_visible_already_in_world_view(self):
        source = Path("carendmr/ui_qt/qrz_window.py").read_text(encoding="utf-8")
        self.assertNotIn("if (zoom < 3 || zoom > 9) return;", source)
        self.assertIn("if (zoom <= 5)", source)
        self.assertIn("weight:2.2", source)
        self.assertIn("opacity:.90", source)
        self.assertIn("fillOpacity:.035", source)

    def test_ham_grid_has_two_and_four_character_labels(self):
        source = Path("carendmr/ui_qt/qrz_window.py").read_text(encoding="utf-8")
        self.assertIn("function fieldName", source)
        self.assertIn("function squareName", source)
        self.assertIn("gridLabel(fieldName", source)
        self.assertIn("gridLabel(squareName", source)

    def test_example_config_documents_maptiler_key(self):
        data = json.loads(Path("config/qrz.example.json").read_text(encoding="utf-8"))
        self.assertIn("maptiler_api_key", data)


if __name__ == "__main__":
    unittest.main()
