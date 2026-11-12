from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")

def test_exit_button_present_and_accessible():
    text = read("carendmr/ui_qt/easy_window.py")
    assert 'EasyButton("Beenden")' in text
    assert 'setAccessibleName("CarenDMR Easy beenden")' in text
    assert "self.exit_button.clicked.connect(self._exit_application)" in text

def test_exit_in_tab_order_and_focus_loop():
    text = read("carendmr/ui_qt/easy_window.py")
    assert "QWidget.setTabOrder(self.ptt_button, self.exit_button)" in text
    assert "self.ptt_button, self.exit_button" in text

def test_exit_always_enabled():
    text = read("carendmr/ui_qt/easy_window.py")
    assert "self.exit_button.setEnabled(True)" in text

def test_exit_stops_tx_and_disconnects():
    text = read("carendmr/ui_qt/easy_window.py")
    assert "def _exit_application" in text
    assert "self._tx_stop_event.set()" in text
    assert "self.controller.disconnect(wait_timeout=3.0)" in text
    assert "dürfen das Programmende niemals verhindern" in text

def test_syntax():
    ast.parse(read("carendmr/ui_qt/easy_window.py"))
