from pathlib import Path
from _ui_sources import main_window_source

ROOT = Path(__file__).resolve().parents[1]
MAIN = main_window_source()
LIVE = (ROOT / "carendmr/brandmeister/live_voice_transmit.py").read_text(encoding="utf-8")
MANAGER = (ROOT / "carendmr/application/connection_manager.py").read_text(encoding="utf-8")
SERVICE = (ROOT / "carendmr/application/parrot_test_service.py").read_text(encoding="utf-8")


def test_tx_complete_callback_is_fired_after_last_dmrd_frame():
    marker = LIVE.index("timing_mark('TX_LETZTER_FRAME_GESENDET')")
    callback = LIVE.index("tx_complete_callback()", marker)
    parrot_wait = LIVE.index('timing_mark("PARROT_RX_RESET_START")', marker)
    assert marker < callback < parrot_wait


def test_tx_complete_callback_is_wired_to_qt_update_queue():
    assert "tx_complete_callback=tx_complete_callback" in SERVICE
    assert "tx_complete_callback=tx_complete_callback" in MANAGER
    assert 'tx_complete_callback=lambda: self._updates.put(("tx_wire_complete", None))' in MAIN


def test_stop_beep_is_triggered_by_wire_complete_not_tx_result():
    wire = MAIN[MAIN.index('elif kind == "tx_wire_complete"'):MAIN.index('elif kind == "tx_result"')]
    result = MAIN[MAIN.index('elif kind == "tx_result"'):MAIN.index('elif kind == "tx_error"')]
    assert "_play_tx_stop_beeps" in wire
    assert "_play_tx_stop_beeps" not in result
    assert '_finish_tx("Sendung beendet; Empfang wieder aktiv.")' in result


def test_ptt_remains_locked_during_tx_shutdown_and_parrot_wait():
    stop = MAIN[MAIN.index("def _stop_tx"):MAIN.index("def _finish_tx")]
    assert "self.ptt_button.setEnabled(False)" in stop
    assert 'self.tx_status.setText("TX wird beendet")' in stop
    assert 'self.tx_status.setText("Warte auf Antwort")' in MAIN
