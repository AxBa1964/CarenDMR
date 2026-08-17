from pathlib import Path

def test_live_tx_has_encoder_pipeline_and_prebuffer():
    source = Path("carendmr/brandmeister/live_voice_transmit.py").read_text(encoding="utf-8")
    assert "CarenDMR-TX-PCM-Feeder" in source
    assert "CarenDMR-TX-MD380-Encoder" in source
    assert "TX_ENCODER_PUFFER_BEREIT" in source
    assert "TX_ENCODER_PUFFER_STATISTIK" in source
    assert "while len(prebuffer_words) < 12" in source
