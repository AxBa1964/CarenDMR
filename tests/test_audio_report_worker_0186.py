from pathlib import Path


def test_tx_capture_does_not_build_report_in_realtime_path():
    source = Path('carendmr/application/audio_send_service.py').read_text(encoding='utf-8')
    assert 'build_session_report(' not in source
    assert 'TX_AUDIO_LAB_DATEN_GESICHERT' in source


def test_reports_are_scheduled_after_network_path():
    live = Path('carendmr/brandmeister/live_voice_transmit.py').read_text(encoding='utf-8')
    listen = Path('carendmr/brandmeister/listen.py').read_text(encoding='utf-8')
    assert 'schedule_session_report(' in live
    assert 'schedule_session_report(' in listen


def test_spectrogram_clamps_zero_power_before_logarithm():
    source = Path('carendmr/diagnostics/audio_lab.py').read_text(encoding='utf-8')
    assert 'np.maximum(power,1e-12)' in source
    assert '.specgram(' not in source
