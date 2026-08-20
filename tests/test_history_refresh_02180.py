from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def test_version():
    assert '__version__ = "0.2.1.81"' in read("carendmr/version.py")


def test_refresh_updates_detail_from_fresh_summary():
    text = read("carendmr/ui_qt/history_widget.py")
    assert "self._show_summary(self._rows[restore_row])" in text
    assert "self._show_summary(self._rows[0])" in text


def test_syntax():
    ast.parse(read("carendmr/ui_qt/history_widget.py"))
    ast.parse(read("carendmr/version.py"))
