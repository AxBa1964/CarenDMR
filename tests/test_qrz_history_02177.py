from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
def read(rel): return (ROOT / rel).read_text(encoding="utf-8")

def test_qrz_removed_from_current_station():
    text = read("carendmr/ui_qt/main_window.py")
    assert 'setAccessibleName("Aktuelles QSO bei QRZ.com loggen")' not in text
    assert "def _log_current_qso_to_qrz" not in text

def test_qrz_is_in_history():
    text = read("carendmr/ui_qt/history_widget.py")
    assert 'QPushButton("Bei QRZ loggen")' in text
    assert 'setAccessibleName("Ausgewähltes QSO bei QRZ.com loggen")' in text
    assert "def _log_selected_to_qrz" in text

def test_history_qrz_status():
    text = read("carendmr/ui_qt/main_window.py")
    assert "def _history_qrz_status" in text
    assert 'return f"Gespeichert · LOGID {logid}"' in text
    assert "self.history_widget.refresh()" in text

def test_only_confirmed_qso_can_log():
    text = read("carendmr/ui_qt/history_widget.py")
    assert "summary.worked and summary.worked_at and summary.callsign" in text

def test_syntax():
    ast.parse(read("carendmr/ui_qt/history_widget.py"))
    ast.parse(read("carendmr/ui_qt/main_window.py"))
