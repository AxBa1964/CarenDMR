import wave
from pathlib import Path
from carendmr.application.audio_send_service import AudioSendService, LivePcmCapture

def test_write_mono_pcm16_wav(tmp_path: Path):
    target = tmp_path / 'audio' / 'probe.wav'
    samples = [0, 1000, -1000, 32767, -32768]
    LivePcmCapture._write_mono_pcm16_wav(target, 16000, samples)
    with wave.open(str(target), 'rb') as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        assert wav_file.getframerate() == 16000
        assert wav_file.getnframes() == len(samples)


def test_audio_debug_wav_default_off_and_persisted(tmp_path):
    service = AudioSendService(tmp_path, backend=object())
    assert service.audio_debug_wav_enabled is False
    service.set_audio_debug_wav_enabled(True)
    service.save_settings()
    reloaded = AudioSendService(tmp_path, backend=object())
    assert reloaded.audio_debug_wav_enabled is True
