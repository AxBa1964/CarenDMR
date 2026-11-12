from pathlib import Path


def test_timeslot_and_call_type_accessibility_are_centralized() -> None:
    source = Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
    manager = Path("carendmr/ui_qt/accessibility_manager.py").read_text(encoding="utf-8")
    assert "def _sync_radio_controls" in source
    assert '"Timeslot 1"' in source
    assert '"Timeslot 2"' in source
    assert '"Gruppenruf"' in source
    assert '"Privatruf"' in source
    assert 'button.setAccessibleName("")' in source
    assert 'setCheckable(True)' not in source
    assert "self.accessibility.announce_timeslot" in source
    assert "self.accessibility.announce_call_type" in source
    assert "def announce_timeslot" in manager
    assert "def announce_call_type" in manager
