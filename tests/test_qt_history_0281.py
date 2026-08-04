from pathlib import Path


def test_history_tab_handling_uses_explicit_focus_targets():
    source = (Path(__file__).parents[1] / "carendmr" / "ui_qt" / "history_widget.py").read_text(encoding="utf-8")
    assert "tab_forward_target" in source
    assert "tab_backward_target" in source
    assert "self.focusNextPrevChild(" not in source
    assert "target.setFocus" in source


def test_operation_shows_current_station_worked_status():
    source = (Path(__file__).parents[1] / "carendmr" / "ui_qt" / "main_window.py").read_text(encoding="utf-8")
    assert 'station_form.addRow("QSO-Status:", self.qso_status_label)' in source
    assert "self.receive_service.history.is_worked(call.source_id)" in source
    assert "def _history_worked_changed" in source
