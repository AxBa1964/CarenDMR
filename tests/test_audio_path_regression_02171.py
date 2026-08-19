from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "audio_path_regression.py"


def test_audio_qs_enables_observer_buffers():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "service.set_audio_debug_wav_enabled(True)" in text


def test_audio_qs_rejects_empty_tx_measurement_with_real_tx():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "voice_bursts_sent" in text
    assert "not capture._ambe_pcm_8k" in text
    assert "Audio-QS-Instrumentierung leer" in text


def test_audio_qs_keeps_all_productive_measurement_points():
    text = SCRIPT.read_text(encoding="utf-8")
    for key in (
        "reference_source",
        "mic_raw_16k",
        "after_mic_gain_16k",
        "after_tx_processing_16k",
        "before_ambe_8k",
        "rx_after_ambe_8k",
        "rx_before_soundcard_8k",
    ):
        assert key in text


def test_audio_qs_syntax():
    ast.parse(SCRIPT.read_text(encoding="utf-8"))
