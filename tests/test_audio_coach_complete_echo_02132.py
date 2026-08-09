from pathlib import Path

def test_audio_coach_tracks_expected_rx_length():
    source = Path("carendmr/application/audio_send_service.py").read_text(encoding="utf-8")
    assert "self._audio_test_expected_rx_samples = 0" in source
    assert "expected_samples: int = 0" in source
    assert "minimum_complete = int(expected * 0.85)" in source
    assert "AUDIO_TEST_PARROT_TERMINATOR_IGNORIERT" in source

def test_parrot_service_passes_actual_tx_duration():
    source = Path("carendmr/application/parrot_test_service.py").read_text(encoding="utf-8")
    assert "expected_samples=int(round(duration * 8000.0))" in source
    duration_pos = source.index("duration=capture.duration_seconds")
    mark_pos = source.index("mark_audio_test_waiting_for_rx")
    assert duration_pos < mark_pos
