from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EASY = (ROOT / "carendmr" / "ui_qt" / "easy_window.py").read_text(encoding="utf-8")

def test_easy_tab_controls_have_explicit_strong_focus():
    assert "self.talkgroup_edit.setFocusPolicy(Qt.FocusPolicy.StrongFocus)" in EASY
    assert "self.connect_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)" in EASY
    assert "self.ptt_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)" in EASY

def test_easy_tab_order_remains_explicit():
    assert "QWidget.setTabOrder(self.talkgroup_edit, self.connect_button)" in EASY
    assert "QWidget.setTabOrder(self.connect_button, self.ptt_button)" in EASY

def test_easy_has_own_visible_focus_style():
    assert "QLineEdit#easyTalkgroupEdit:focus" in EASY
    assert "QPushButton#easyConnectButton:focus" in EASY
    assert "QPushButton#easyPttButton:focus" in EASY
    assert "5px solid #FFD54A" in EASY
