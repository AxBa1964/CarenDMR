from pathlib import Path


def source() -> str:
    return Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")


def test_desktop_ptt_is_toggle_not_hold_to_talk():
    text = source()
    assert "self.ptt_button.clicked.connect(self._toggle_tx)" in text
    assert "self._tx_active" in text
    assert "self._stop_tx()" in text


def test_existing_hotkey_manager_is_used_in_qt():
    text = source()
    assert "HotkeyManager" in text
    assert "_handle_space_shortcut" in text
    assert "_toggle_timeslot" in text
    assert "_toggle_call_type" in text


def test_talkgroup_uses_native_numeric_widget():
    text = source()
    assert "QLineEdit" in text
    assert "TalkgroupSearchWidget" in text
    assert 'setMaxLength(64)' in text
    assert 'Talkgroup nach Nummer oder Name suchen' in text
