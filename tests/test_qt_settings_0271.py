from pathlib import Path
from _ui_sources import main_window_source


def test_settings_contains_hotkey_management():
    source = (Path(__file__).parents[1] / "carendmr" / "ui_qt" / "settings_dialog.py").read_text(encoding="utf-8")
    assert "HotkeyManager" in source
    assert "Werkseinstellungen" in source
    assert "doppelt belegt" in source


def test_operation_contains_restored_information():
    source = main_window_source()
    for label in ("Ort / Region", "Land", "Empfang", "Letztes Ereignis"):
        assert label in source
    assert "_reload_hotkeys" in source
