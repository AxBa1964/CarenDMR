from pathlib import Path
from _ui_sources import main_window_source


def source() -> str:
    return main_window_source()


def test_desktop_ptt_is_toggle_not_hold_to_talk():
    text = source()
    assert "self.ptt_button.clicked.connect(self._toggle_tx)" in text
    assert "self._tx_active" in text
    assert "self._stop_tx()" in text


def test_existing_hotkey_manager_is_used_in_qt():
    text = source()
    assert "self.hotkey_manager = self.services.hotkeys" in text
    bootstrap = Path("carendmr/bootstrap.py").read_text(encoding="utf-8")
    assert 'HotkeyManager(config / "hotkeys.local.json")' in bootstrap
    assert "_handle_space_shortcut" in text
    assert "_toggle_timeslot" in text
    assert "_toggle_call_type" in text


def test_talkgroup_uses_native_numeric_widget():
    text = source()
    assert "QLineEdit" in text
    assert "TalkgroupSearchWidget" in text
    assert 'setMaxLength(64)' in text
    assert 'Talkgroup nach Nummer oder Name suchen' in text
