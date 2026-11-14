from pathlib import Path
from _ui_sources import main_window_source


def test_history_tab_handling_uses_explicit_focus_targets():
    source = (Path(__file__).parents[1] / "carendmr" / "ui_qt" / "history_widget.py").read_text(encoding="utf-8")
    assert "tab_forward_target" in source
    assert "tab_backward_target" in source
    assert "self.focusNextPrevChild(" not in source
    assert "target.setFocus" in source


def test_operation_shows_current_station_worked_status():
    source = main_window_source()
    assert 'self.qso_status_label = QLabel("Keine Station aktiv")' in source
    assert '("QSO-Status", self.qso_status_label)' in source
    assert "self.receive_service.history.last_worked_at(call.source_id)" in source
    assert "def _history_worked_changed" in source
