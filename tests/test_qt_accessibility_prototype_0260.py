from pathlib import Path


def test_qt_prototype_uses_native_widgets_and_accessible_metadata():
    source = Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
    assert "QMainWindow" in source
    assert "QLineEdit" in source
    assert "TalkgroupSearchWidget" in source
    assert 'self.tg_edit.setAccessibleName("Talkgroup")' in source
    assert "AccessibilityManager" in source


def test_desktop_speech_is_disabled_in_saved_preferences():
    source = Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
    assert "OperatingPreferences(" in source
    assert ", False," in source
    assert "keine eigene TTS" in source or "keine eigene TTS" in source.lower()
