from pathlib import Path
import unittest


class QrzMapResize02150Tests(unittest.TestCase):
    def test_html_hides_browser_scrollbars(self):
        source = Path("carendmr/ui_qt/qrz_window.py").read_text(encoding="utf-8")
        self.assertIn("overflow: hidden", source)
        self.assertIn("#map {{ position: absolute; inset: 0;", source)

    def test_leaflet_invalidate_size_is_centralized(self):
        source = Path("carendmr/ui_qt/qrz_window.py").read_text(encoding="utf-8")
        self.assertIn("function syncMapSize()", source)
        self.assertIn("map.invalidateSize({{pan:false, debounceMoveend:true}})", source)
        self.assertIn("syncMapSize();\n    const points", source)
        self.assertIn("syncMapSize();\n    if (stationData.remote)", source)

    def test_webview_resyncs_after_load(self):
        source = Path("carendmr/ui_qt/qrz_window.py").read_text(encoding="utf-8")
        self.assertIn("self.map_view.loadFinished.connect(self._map_loaded)", source)
        self.assertIn("def _map_loaded", source)
        self.assertIn('syncMapSize(); worldView();', source)

    def test_webview_resyncs_after_window_resize(self):
        source = Path("carendmr/ui_qt/qrz_window.py").read_text(encoding="utf-8")
        self.assertIn("def resizeEvent", source)
        self.assertIn("typeof syncMapSize === 'function'", source)

    def test_world_and_detail_buttons_resync_map(self):
        source = Path("carendmr/ui_qt/qrz_window.py").read_text(encoding="utf-8")
        self.assertIn("typeof worldView === 'function'", source)
        self.assertIn("typeof detailView === 'function'", source)


if __name__ == "__main__":
    unittest.main()
