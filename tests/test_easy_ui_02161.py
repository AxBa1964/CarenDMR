from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EASY = (ROOT / "carendmr" / "ui_qt" / "easy_window.py").read_text(encoding="utf-8")

def test_easy_tx_end_cue_is_called_directly_from_wire_complete_callback():
    assert "tx_complete_callback=self._tx_wire_complete" in EASY
    assert "def _tx_wire_complete(self)" in EASY
    assert "self._play_tx_stop_cue()" in EASY

def test_easy_tx_end_cue_no_longer_waits_for_qt_update_queue():
    assert 'self._updates.put(("tx_wire_complete", None))' not in EASY

def test_easy_tx_end_cue_errors_are_diagnostic_but_do_not_break_radio():
    assert "[EASY][AUDIO-CUE] TX-Endton fehlgeschlagen" in EASY
