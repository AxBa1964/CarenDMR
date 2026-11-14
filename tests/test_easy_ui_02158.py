from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = (ROOT / "carendmr" / "application" / "operating_controller.py").read_text(encoding="utf-8")
EASY = (ROOT / "carendmr" / "ui_qt" / "easy_window.py").read_text(encoding="utf-8")

def test_tx_keeps_operating_state_while_rx_is_paused():
    assert "self.radio_state.state is RadioState.TRANSMITTING and target is not RadioState.ERROR" in CONTROLLER

def test_easy_connect_button_has_explicit_accessible_name():
    assert 'EasyButton("Verbinden")' in EASY
    assert 'self.connect_button.setAccessibleName("Verbinden")' in EASY

def test_easy_ptt_stop_sets_existing_stop_event():
    assert "self._tx_stop_event.set()" in EASY
    assert "tx_complete_callback=self._tx_wire_complete" in EASY
    assert "def _tx_wire_complete(self)" in EASY
