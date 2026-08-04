from pathlib import Path


def source() -> str:
    return Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")


def test_desktop_ptt_is_toggle_not_hold_to_talk():
    text = source()
    assert "self.ptt_button.setCheckable(True)" in text
    assert "self.ptt_button.clicked.connect(self._toggle_tx_keyboard)" in text
    assert "self.ptt_button.pressed.connect" not in text
    assert "self.ptt_button.released.connect" not in text


def test_existing_hotkey_manager_is_used_in_qt():
    text = source()
    assert "HotkeyManager" in text
    assert '"PTT": self._toggle_tx_keyboard' in text
    assert "ApplicationShortcut" in text
    assert "setAutoRepeat(False)" in text


def test_talkgroup_uses_native_numeric_widget():
    text = source()
    assert "QLineEdit" in text
    assert "QIntValidator" in text
    assert "setMaxLength(8)" in text
    assert "_update_talkgroup_accessibility" in text
    assert "talkgroup_edit.selectAll()" in text
