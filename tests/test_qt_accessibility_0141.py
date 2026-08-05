from pathlib import Path


def test_ptt_does_not_emit_own_tx_rx_announcements() -> None:
    source = Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
    start = source[source.index("def _start_tx"):source.index("def _stop_tx")]
    finish = source[source.index("def _finish_tx"):source.index("def _verify_encoder")]
    assert "_announce_radio_state" not in start
    assert "_announce_radio_state" not in finish


def test_ptt_keeps_focus_while_stopping() -> None:
    source = Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
    stop = source[source.index("def _stop_tx"):source.index("def _finish_tx")]
    assert "self._tx_stopping = True" in stop
    assert "self.ptt_button.setEnabled(True)" in stop
    assert "self.ptt_button.setEnabled(False)" not in stop


def test_radio_accessible_names_do_not_duplicate_selection_state() -> None:
    source = Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
    block = source[source.index("def _sync_radio_controls"):source.index("def _target")]
    assert 'button.setAccessibleName("")' in block
    assert "nicht ausgewählt" not in block
    assert "Kontrollkästchen" not in block
