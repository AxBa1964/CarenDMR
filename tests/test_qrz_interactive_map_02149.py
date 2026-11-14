from pathlib import Path
import unittest
from _ui_sources import main_window_source


class QrzInteractiveMap02149Tests(unittest.TestCase):
    def test_qrz_button_retains_geometry_without_placeholder_widget(self):
        source = main_window_source()
        self.assertIn("setRetainSizeWhenHidden(True)", source)
        self.assertNotIn("qrz_slot = QWidget", source)
        self.assertIn("Qt.AlignmentFlag.AlignLeft", source)

    def test_qrz_window_uses_interactive_web_map(self):
        source = Path("carendmr/ui_qt/qrz_window.py").read_text(encoding="utf-8")
        self.assertIn("QWebEngineView", source)
        self.assertIn("leaflet@1.9.4", source)
        self.assertIn("tile.openstreetmap.org", source)
        self.assertIn("scrollWheelZoom: true", source)
        self.assertIn("worldCopyJump: true", source)

    def test_map_has_world_detail_grid_and_route(self):
        source = Path("carendmr/ui_qt/qrz_window.py").read_text(encoding="utf-8")
        self.assertIn("function worldView()", source)
        self.assertIn("function detailView()", source)
        self.assertIn("function drawHamGrid()", source)
        self.assertIn("L.polyline(", source)
        self.assertIn("distanceKm", source)
        self.assertIn("bearing", source)

    def test_profile_card_is_compact_and_image_is_larger(self):
        source = Path("carendmr/ui_qt/qrz_window.py").read_text(encoding="utf-8")
        self.assertIn("self.image_label.setFixedSize(300, 300)", source)
        self.assertIn("details.setColumnMinimumWidth(0, 92)", source)
        self.assertIn('("Entfernung", distance_text)', source)
        self.assertIn("_yes_no(profile.lotw)", source)
        self.assertIn("_yes_no(profile.eqsl)", source)

    def test_satellite_is_not_faked_with_deprecated_public_tiles(self):
        source = Path("carendmr/ui_qt/qrz_window.py").read_text(encoding="utf-8")
        self.assertIn('self.satellite_button = QPushButton("Satellit")', source)
        self.assertIn("self.satellite_button.setEnabled(bool(self.maptiler_api_key))", source)
        self.assertNotIn("World_Imagery", source)
        self.assertNotIn("server.arcgisonline.com", source)


if __name__ == "__main__":
    unittest.main()
