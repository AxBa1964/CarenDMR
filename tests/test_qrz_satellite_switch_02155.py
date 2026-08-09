from pathlib import Path
import unittest

class QrzSatelliteSwitch02155Tests(unittest.TestCase):
    def test_satellite_uses_maptiler_leaflet_hidpi_url(self):
        source = Path("carendmr/ui_qt/qrz_window.py").read_text(encoding="utf-8")
        self.assertIn(
            "https://api.maptiler.com/maps/satellite-v4/{{z}}/{{x}}/{{y}}@2x.jpg?key=",
            source,
        )
        self.assertIn("tileSize: 512", source)
        self.assertIn("zoomOffset: -1", source)

    def test_base_layer_switch_is_explicit(self):
        source = Path("carendmr/ui_qt/qrz_window.py").read_text(encoding="utf-8")
        self.assertIn("map.removeLayer(osm)", source)
        self.assertIn("satellite.addTo(map)", source)
        self.assertIn("map.removeLayer(satellite)", source)
        self.assertIn("osm.addTo(map)", source)

    def test_map_source_indicator_changes(self):
        source = Path("carendmr/ui_qt/qrz_window.py").read_text(encoding="utf-8")
        self.assertIn("map-source-info", source)
        self.assertIn("source.innerHTML = 'Satellit'", source)
        self.assertIn("source.innerHTML = 'Karte'", source)

    def test_tile_errors_are_logged(self):
        source = Path("carendmr/ui_qt/qrz_window.py").read_text(encoding="utf-8")
        self.assertIn("satellite.on('tileerror'", source)
        self.assertIn("CarenDMR MapTiler satellite tile failed", source)

if __name__ == "__main__":
    unittest.main()
