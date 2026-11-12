from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
THEME = (ROOT / "carendmr/ui_qt/theme.py").read_text(encoding="utf-8")


def test_target_selection_is_persisted_immediately():
    ts_block = MAIN[MAIN.index("def _select_timeslot"):MAIN.index("def _select_call_type")]
    call_block = MAIN[MAIN.index("def _select_call_type"):MAIN.index("def _persist_current_target")]
    assert "self._persist_current_target()" in ts_block
    assert "self._persist_current_target()" in call_block
    assert "self.preferences_store.save" in MAIN


def test_tx_button_keeps_tx_label_and_uses_ready_and_tx_states():
    assert 'self.ptt_button.setText("RX")' not in MAIN
    assert 'self.ptt_button.setText("TX")' in MAIN
    assert 'visualState", "ready"' in MAIN
    assert 'visualState", "tx"' in MAIN
    assert 'QPushButton#pttButton[visualState="ready"]' in THEME
    assert 'QPushButton#pttButton[visualState="tx"]' in THEME


def test_tx_counter_is_only_started_in_actual_tx_and_cleared_on_stop():
    begin = MAIN[MAIN.index("def _begin_tx"):MAIN.index("def _cancel_pending_tx")]
    stop = MAIN[MAIN.index("def _stop_tx"):MAIN.index("def _finish_tx")]
    assert 'self._tx_elapsed_seconds = 0' in begin
    assert 'self._tx_elapsed_timer.start()' in begin
    assert 'self._tx_elapsed_timer.stop()' in stop
    assert 'self._tx_elapsed_seconds = 0' in stop
