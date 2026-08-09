from pathlib import Path
import unittest

class QrzFlagMarkers02153Tests(unittest.TestCase):
    def test_map_uses_flag_pin_icons_for_both_station_roles(self):
        source = Path("carendmr/ui_qt/qrz_window.py").read_text(encoding="utf-8")
        self.assertIn("function flagPinIcon(role)", source)
        self.assertIn("'own'", source)
        self.assertIn("'remote'", source)
        self.assertIn("Eigener Standort", source)
        self.assertIn("Gegenstation", source)

    def test_old_plain_dot_marker_is_removed(self):
        source = Path("carendmr/ui_qt/qrz_window.py").read_text(encoding="utf-8")
        self.assertNotIn("function markerIcon(color)", source)
        self.assertNotIn("width:15px;height:15px;border-radius:50%", source)

    def test_marker_popup_contains_station_information(self):
        source = Path("carendmr/ui_qt/qrz_window.py").read_text(encoding="utf-8")
        self.assertIn("point.name", source)
        self.assertIn("point.grid", source)
        self.assertIn("point.country", source)
        self.assertIn("point.lat.toFixed(4)", source)
        self.assertIn("point.lon.toFixed(4)", source)

    def test_existing_world_detail_and_route_are_preserved(self):
        source = Path("carendmr/ui_qt/qrz_window.py").read_text(encoding="utf-8")
        self.assertIn("function worldView()", source)
        self.assertIn("function detailView()", source)
        self.assertIn("L.polyline(", source)
        self.assertIn("remoteMarker.openPopup()", source)

if __name__ == "__main__":
    unittest.main()
