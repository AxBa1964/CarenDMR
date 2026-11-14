from pathlib import Path
from _ui_sources import main_window_source


def test_qt_prototype_uses_native_widgets_and_accessible_metadata():
    source = main_window_source()
    assert "QMainWindow" in source
    assert "QLineEdit" in source
    assert "TalkgroupSearchWidget" in source
    assert 'self.tg_edit.setAccessibleName("Talkgroup")' in source
    assert "AccessibilityManager" in source


def test_desktop_speech_is_disabled_in_saved_preferences():
    source = main_window_source()
    assert "OperatingPreferences(" in source
    assert ", False," in source
    assert "keine eigene TTS" in source or "keine eigene TTS" in source.lower()
