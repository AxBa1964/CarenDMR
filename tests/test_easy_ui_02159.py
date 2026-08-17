from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EASY = (ROOT / "carendmr" / "ui_qt" / "easy_window.py").read_text(encoding="utf-8")

def test_connect_button_accessible_names_follow_state():
    assert 'self.connect_button.setAccessibleName("Verbinden")' in EASY
    assert 'self.connect_button.setAccessibleName("Trennen")' in EASY

def test_tx_end_double_beep_is_immediate_after_wire_complete():
    assert 'tx_complete_callback=self._tx_wire_complete' in EASY
    assert 'self._play_tx_stop_cue()' in EASY

def test_ptt_start_feedback_remains_short():
    assert 'self.ptt_button, "Senden."' in EASY
