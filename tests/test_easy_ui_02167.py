from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EASY = (ROOT / "carendmr" / "ui_qt" / "easy_window.py").read_text(encoding="utf-8")
THEME = (ROOT / "carendmr" / "ui_qt" / "theme.py").read_text(encoding="utf-8")

def test_easy_installs_tab_event_filter_on_all_three_controls():
    assert "control.installEventFilter(self)" in EASY
    assert "def eventFilter(self, watched, event)" in EASY
    assert "Qt.Key.Key_Tab" in EASY
    assert "Qt.Key.Key_Backtab" in EASY
    assert "Qt.FocusReason.TabFocusReason" in EASY
    assert "Qt.FocusReason.BacktabFocusReason" in EASY

def test_easy_keeps_native_focus_enabled():
    assert "apply_theme(app, suppress_native_focus=False)" in EASY
    assert "def apply_theme(app: QApplication, *, suppress_native_focus: bool = True)" in THEME

def test_normal_theme_behavior_remains_default():
    assert "if suppress_native_focus and not isinstance(app.style(), CarenProxyStyle):" in THEME
