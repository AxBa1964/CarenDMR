from pathlib import Path

from carendmr.application.audio_send_service import AudioSendService


def test_audio_test_state_is_not_persisted(tmp_path):
    service = AudioSendService(tmp_path, backend=object())
    service._audio_test_armed = True
    service._audio_debug_wav_enabled = True
    service.save_settings()
    text = (tmp_path / "config" / "audio_send.local.json").read_text(encoding="utf-8")
    assert '"audio_debug_wav_enabled": false' in text


def test_guided_test_uses_single_audio_test_directory_source():
    source = Path("carendmr/application/audio_send_service.py").read_text(encoding="utf-8")
    assert 'f"AudioTest_{stamp}"' in source
    assert "_audio_test_session_dir" in source


def test_receive_debug_directory_is_resolved_lazily():
    source = Path("carendmr/brandmeister/listen.py").read_text(encoding="utf-8")
    assert "def resolve_session_dir" in source
    assert "if values and resolve_session_dir() is not None" in source
