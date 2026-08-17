from pathlib import Path


def _source() -> str:
    return (Path(__file__).parents[1] / "carendmr" / "ui_qt" / "settings_dialog.py").read_text(encoding="utf-8")


def test_hotkey_table_allows_tab_to_leave():
    assert "setTabKeyNavigation(False)" in _source()


def test_factory_reset_requires_confirmation():
    source = _source()
    assert '"Werkseinstellungen wiederherstellen"' in source
    assert "QMessageBox.StandardButton.No" in source
    assert "Zurücksetzen wurde abgebrochen." in source
