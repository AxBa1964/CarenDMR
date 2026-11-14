from pathlib import Path
from _ui_sources import main_window_source


def test_timeslot_and_call_type_accessibility_are_centralized() -> None:
    source = main_window_source()
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
