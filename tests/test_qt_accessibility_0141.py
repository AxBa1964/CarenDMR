from pathlib import Path
from _ui_sources import main_window_source


def test_ptt_does_not_emit_own_tx_rx_announcements() -> None:
    source = main_window_source()
    start = source[source.index("def _start_tx"):source.index("def _stop_tx")]
    finish = source[source.index("def _finish_tx"):source.index("def _verify_encoder")]
    assert "_announce_radio_state" not in start
    assert "_announce_radio_state" not in finish


def test_ptt_keeps_focus_while_stopping() -> None:
    source = main_window_source()
    stop = source[source.index("def _stop_tx"):source.index("def _finish_tx")]
    assert "self._tx_stopping = True" in stop
    assert "self.ptt_button.setEnabled(False)" in stop
    assert 'self.tx_status.setText("TX wird beendet")' in stop


def test_radio_accessible_names_do_not_duplicate_selection_state() -> None:
    source = main_window_source()
    block = source[source.index("def _sync_radio_controls"):source.index("def _target")]
    assert 'button.setAccessibleName("")' in block
    assert "nicht ausgewählt" not in block
    assert "Kontrollkästchen" not in block
