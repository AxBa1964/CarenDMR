from pathlib import Path

from carendmr.accessibility.hotkeys import DEFAULT_HOTKEYS, REQUIRED_HOTKEYS, HotkeyManager

MAIN = Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
SETTINGS = Path("carendmr/ui_qt/settings_dialog.py").read_text(encoding="utf-8")


def test_ts_and_call_type_are_not_in_tab_order():
    assert "button.setFocusPolicy(Qt.FocusPolicy.NoFocus)" in MAIN
    assert "QWidget.setTabOrder(self.tg_edit, self.connect_button)" in MAIN


def test_hotkey_hints_are_dynamic():
    assert "def _update_radio_hotkey_hints" in MAIN
    assert 'mapping.get("TS_CHANGE")' in MAIN
    assert 'mapping.get("CALLTYPE_CHANGE")' in MAIN


def test_required_hotkeys_are_protected():
    assert {"CONNECT", "TS_CHANGE", "CALLTYPE_CHANGE", "PTT"} <= REQUIRED_HOTKEYS
    assert "REQUIRED_HOTKEYS" in SETTINGS
    assert "Diese Kernfunktion benötigt zwingend einen Hotkey" in SETTINGS


def test_required_hotkey_empty_value_falls_back_to_default(tmp_path):
    path = tmp_path / "hotkeys.local.json"
    path.write_text('{"TS_CHANGE": ""}', encoding="utf-8")
    manager = HotkeyManager(path)
    assert manager.mapping["TS_CHANGE"] == DEFAULT_HOTKEYS["TS_CHANGE"]
