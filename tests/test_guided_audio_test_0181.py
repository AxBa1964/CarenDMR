from pathlib import Path

from carendmr.application.audio_send_service import AudioSendService, LivePcmCapture


def test_guided_audio_test_api_exists():
    assert hasattr(AudioSendService, "arm_audio_test")
    assert hasattr(AudioSendService, "cancel_audio_test")
    assert hasattr(AudioSendService, "audio_test_armed")


def test_pre_roll_measurement_point_exists():
    source = Path("carendmr/application/audio_send_service.py").read_text(encoding="utf-8")
    assert "00_vor_ptt_mikrofon_16k.wav" in source
    assert "CarenDMR-AudioTest-Vorlauf" in source


def test_settings_offer_guided_audio_test():
    source = Path("carendmr/ui_qt/settings_dialog.py").read_text(encoding="utf-8")
    assert "Geführten Audio-Test starten" in source
    assert "Audio-Test abbrechen" in source
    assert "2 Sekunden vor PTT" in source


def test_analysis_dependencies_are_declared():
    requirements = Path("requirements.txt").read_text(encoding="utf-8").lower()
    for package in ("matplotlib", "scipy", "soundfile", "librosa"):
        assert package in requirements
