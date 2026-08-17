from pathlib import Path
import unittest


class QrzLeafletBounds02152Tests(unittest.TestCase):
    def test_map_has_initial_view_before_layers_are_added(self):
        source = Path("carendmr/ui_qt/qrz_window.py").read_text(encoding="utf-8")
        self.assertIn("}}).setView([20, 0], 2);", source)
        constructor = source.index("const map = L.map")
        tile_layer = source.index("const osm = L.tileLayer")
        self.assertLess(constructor, tile_layer)

    def test_grid_does_not_read_bounds_before_map_is_loaded(self):
        source = Path("carendmr/ui_qt/qrz_window.py").read_text(encoding="utf-8")
        self.assertIn("if (!map._loaded) return;", source)
        self.assertIn("const bounds = map.getBounds();", source)

    def test_resize_sync_uses_non_animated_invalidation(self):
        source = Path("carendmr/ui_qt/qrz_window.py").read_text(encoding="utf-8")
        self.assertIn("map.invalidateSize({{pan:false, debounceMoveend:true}});", source)
        self.assertNotIn("map.invalidateSize(true);", source)


if __name__ == "__main__":
    unittest.main()
