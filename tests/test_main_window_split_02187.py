"""Aufteilung des Hauptfensters in Teilmodule (0.2.1.87)."""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI_QT = ROOT / "carendmr" / "ui_qt"
MIXINS = {
    "main_window_logbook.py": "MainWindowLogbookMixin",
    "main_window_windows.py": "MainWindowWindowsMixin",
    "main_window_audio.py": "MainWindowAudioMixin",
    "main_window_channels.py": "MainWindowChannelsMixin",
    "main_window_radio.py": "MainWindowRadioMixin",
}


def _class(path: Path, name: str) -> ast.ClassDef:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == name)


def _methods(cls: ast.ClassDef) -> set[str]:
    return {n.name for n in cls.body if isinstance(n, ast.FunctionDef)}


class MainWindowSplitTests(unittest.TestCase):
    def test_main_window_inherits_all_mixins(self):
        main = _class(UI_QT / "main_window.py", "MainWindow")
        bases = [ast.unparse(b) for b in main.bases]
        self.assertEqual("QMainWindow", bases[0])
        for mixin in MIXINS.values():
            self.assertIn(mixin, bases)

    def test_mixins_are_plain_classes_without_init(self):
        for filename, name in MIXINS.items():
            cls = _class(UI_QT / filename, name)
            with self.subTest(mixin=name):
                self.assertEqual([], cls.bases)
                self.assertNotIn("__init__", _methods(cls))

    def test_no_method_is_defined_twice(self):
        # Doppelte Namen würden sich über die Vererbung unbemerkt verdecken.
        seen: dict[str, str] = {}
        parts = {"main_window.py": "MainWindow", **MIXINS}
        for filename, name in parts.items():
            for method in _methods(_class(UI_QT / filename, name)):
                with self.subTest(method=method):
                    self.assertNotIn(method, seen, f"{method} in {filename} und {seen.get(method)}")
                seen[method] = filename

    def test_qt_event_handlers_stay_in_main_window(self):
        main = _methods(_class(UI_QT / "main_window.py", "MainWindow"))
        for handler in ("__init__", "closeEvent", "eventFilter", "_build_ui", "_process_updates", "_apply_state"):
            self.assertIn(handler, main)


if __name__ == "__main__":
    unittest.main()
