from pathlib import Path
import unittest


class QrzLeafletBootstrap02151Tests(unittest.TestCase):
    def test_official_leaflet_css_sri_is_used(self):
        source = Path("carendmr/ui_qt/qrz_window.py").read_text(encoding="utf-8")
        self.assertIn(
            'sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=',
            source,
        )
        self.assertNotIn(
            'sha256-p4NxAoJBhIINfQ3yn7WgBT9FViWv5PTKskpC62LhKkA=',
            source,
        )

    def test_map_readiness_is_tracked(self):
        source = Path("carendmr/ui_qt/qrz_window.py").read_text(encoding="utf-8")
        self.assertIn("self._map_ready = False", source)
        self.assertIn("self._map_ready = bool(ok and self.map_view is not None)", source)
        self.assertIn("if self.map_view is not None and self._map_ready:", source)

    def test_qt_js_calls_are_guarded(self):
        source = Path("carendmr/ui_qt/qrz_window.py").read_text(encoding="utf-8")
        self.assertIn("typeof syncMapSize === 'function'", source)
        self.assertIn("typeof worldView === 'function'", source)
        self.assertIn("typeof detailView === 'function'", source)
        self.assertIn("typeof toggleGrid === 'function'", source)

    def test_resize_cannot_call_js_before_map_ready(self):
        source = Path("carendmr/ui_qt/qrz_window.py").read_text(encoding="utf-8")
        self.assertIn("if self.map_view is not None and self._map_ready:", source)


if __name__ == "__main__":
    unittest.main()
