from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "audio_path_regression.py"


def test_audio_path_regression_uses_productive_tx_capture():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "AudioSendService" in text
    assert "start_live_capture" in text
    assert "capture._processed_pcm_16k" in text
    assert "capture._ambe_pcm_8k" in text


def test_audio_path_regression_uses_productive_rx_callback():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "class MeasuringPcmOutput(BufferedPcmOutput)" in text
    assert "super().write(values)" in text
    assert "self._callback(memoryview(out)" in text


def test_audio_path_regression_has_required_kpis():
    text = SCRIPT.read_text(encoding="utf-8")
    for key in (
        "reference_source",
        "mic_raw_16k",
        "after_mic_gain_16k",
        "after_tx_processing_16k",
        "before_ambe_8k",
        "rx_after_ambe_8k",
        "rx_before_soundcard_8k",
        "echo_completeness_percent",
    ):
        assert key in text


def test_audio_path_regression_syntax():
    ast.parse(SCRIPT.read_text(encoding="utf-8"))
