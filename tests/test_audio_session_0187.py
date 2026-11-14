from pathlib import Path


def test_guided_audio_test_uses_one_explicit_session_directory():
    source = Path('carendmr/application/audio_send_service.py').read_text(encoding='utf-8')
    assert 'session_dir=session_dir' in source
    assert 'Für den geführten Audio-Test fehlt der Sitzungsordner' in source
    assert 'f"AudioTest_{stamp}"' in source


def test_parrot_finishes_guided_session_after_network_path():
    parrot = Path('carendmr/application/parrot_test_service.py').read_text(encoding='utf-8')
    service = Path('carendmr/application/audio_send_service.py').read_text(encoding='utf-8')
    assert 'rx_debug_dir=capture.audio_lab_dir' in parrot
    # Die geführte Sitzung endet erst nach gespeicherter Parrot-Antwort.
    saved = service[service.index('"AUDIO_TEST_PARROT_GESPEICHERT"'):]
    assert 'self.finish_audio_test_session()' in saved
