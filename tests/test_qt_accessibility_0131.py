from pathlib import Path
from _ui_sources import main_window_source


def test_native_announcement_event_and_workflow_focus() -> None:
    root = Path(__file__).resolve().parents[1]
    announcer = (root / "carendmr" / "ui_qt" / "accessibility_announcer.py").read_text(encoding="utf-8")
    main = main_window_source()
    assert "QAccessibleAnnouncementEvent" in announcer
    assert "QAccessible.updateAccessibility" in announcer
    assert "_focus_ptt_after_connect" in main
    assert "_focus_talkgroup" in main
