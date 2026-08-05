from pathlib import Path


def test_talkgroup_accessibility_uses_single_confirmation_path() -> None:
    main = Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
    manager = Path("carendmr/ui_qt/accessibility_manager.py").read_text(encoding="utf-8")
    assert "self.tg_edit.textEdited.connect" not in main
    assert "def _talkgroup_text_edited" not in main
    assert "self.accessibility.announce_pending_talkgroup(self.tg_edit, value)" in main
    assert "def announce_pending_talkgroup" in manager
