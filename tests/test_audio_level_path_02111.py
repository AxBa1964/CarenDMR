import json
import wave
from pathlib import Path

from carendmr.diagnostics.audio_lab import build_level_path_report


def _wav(path: Path, samples, rate=16000):
    import array
    pcm = array.array('h', samples)
    with wave.open(str(path), 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(pcm.tobytes())


def test_level_path_reports_linear_mic_gain_and_stage_delta(tmp_path):
    _wav(tmp_path / '01_mikrofon_roh_16k.wav', [4000, -4000] * 800)
    _wav(tmp_path / '02_nach_mic_gain_16k.wav', [1000, -1000] * 800)
    target = build_level_path_report(tmp_path, gain_percent=25)
    payload = json.loads(target.read_text(encoding='utf-8'))
    assert payload['microphone_gain_percent'] == 25
    assert payload['microphone_gain_factor'] == 0.25
    assert -12.1 < payload['microphone_gain_db'] < -12.0
    assert len(payload['stages']) == 2
    assert -12.2 < payload['stages'][1]['delta_rms_from_previous_db'] < -11.9


def test_live_capture_writes_level_path_diagnostic_hook():
    source = Path('carendmr/application/audio_send_service.py').read_text(encoding='utf-8')
    assert 'level_path.json' in Path('carendmr/diagnostics/audio_lab.py').read_text(encoding='utf-8')
    assert 'TX_PEGELPFAD' in source
    assert 'build_level_path_report' in source
