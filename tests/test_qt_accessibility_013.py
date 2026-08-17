from pathlib import Path


def test_accessibility_uses_native_qt_without_own_tts():
    announcer = Path("carendmr/ui_qt/accessibility_announcer.py").read_text(encoding="utf-8")
    manager = Path("carendmr/ui_qt/accessibility_manager.py").read_text(encoding="utf-8")
    assert "QAccessible.updateAccessibility" in announcer
    assert "QAccessibleAnnouncementEvent" in announcer
    assert "pyttsx3" not in announcer + manager
    assert "AccessibilityManager" in manager
