from pathlib import Path

def test_md380_live_gain_is_plus_2_db_and_clipped():
    source = Path("carendmr/encoder/md380_dynarmic.py").read_text(encoding="utf-8")
    assert "MD380_INPUT_GAIN_DB = 2.0" in source
    assert "input_gain_db: float = MD380_INPUT_GAIN_DB" in source
    assert "sample * self._input_gain" in source
    assert "max(-32768, min(32767" in source

def test_live_tx_timing_code_has_no_gain_constant():
    source = Path("carendmr/brandmeister/live_voice_transmit.py").read_text(encoding="utf-8")
    assert "MD380_INPUT_GAIN_DB" not in source
