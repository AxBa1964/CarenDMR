from pathlib import Path


def test_native_announcement_event_and_workflow_focus() -> None:
    root = Path(__file__).resolve().parents[1]
    announcer = (root / "carendmr" / "ui_qt" / "accessibility_announcer.py").read_text(encoding="utf-8")
    main = (root / "carendmr" / "ui_qt" / "main_window.py").read_text(encoding="utf-8")
    assert "QAccessibleAnnouncementEvent" in announcer
    assert "QAccessible.updateAccessibility" in announcer
    assert "_focus_ptt_after_connect" in main
    assert "_focus_talkgroup" in main
