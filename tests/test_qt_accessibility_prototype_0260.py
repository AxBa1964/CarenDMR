from pathlib import Path


def test_qt_prototype_uses_native_widgets_and_accessible_metadata():
    source = Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
    assert "QMainWindow" in source
    assert "QLineEdit" in source
    assert "QComboBox" in source
    assert "QRadioButton" in source
    assert "QPushButton" in source
    assert "setAccessibleName" in source
    assert "setAccessibleDescription" in source
    assert "QWidget.setTabOrder" in source


def test_qt_prototype_reuses_application_services():
    source = Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
    for name in (
        "ConnectionManager", "ReceiveService", "AudioSendService",
        "EncoderService", "ParrotTestService", "RadioStateMachine",
    ):
        assert name in source


def test_desktop_speech_is_disabled_in_saved_preferences():
    source = Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
    assert "OperatingPreferences(talkgroup, timeslot, call_type, False)" in source
