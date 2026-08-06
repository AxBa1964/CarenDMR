from pathlib import Path

from carendmr.application.audio_send_service import AudioSendService


class DummyBackend:
    pass


def test_guided_audio_test_does_not_enable_global_debug(tmp_path: Path):
    service = AudioSendService(tmp_path, backend=DummyBackend())
    service._audio_debug_wav_enabled = False
    # Do not start a real pre-roll thread in this unit test.
    service._audio_test_armed = True
    service._audio_test_session_dir = tmp_path / "AudioTest_x"
    service.finish_audio_test_session()
    assert service.audio_debug_wav_enabled is False
    assert service.audio_test_session_dir is None


def test_finish_guided_test_preserves_user_debug_setting(tmp_path: Path):
    service = AudioSendService(tmp_path, backend=DummyBackend())
    service._audio_debug_wav_enabled = True
    service._audio_test_armed = True
    service._audio_test_session_dir = tmp_path / "AudioTest_x"
    service.finish_audio_test_session()
    assert service.audio_debug_wav_enabled is True
