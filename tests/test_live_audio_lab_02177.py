from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "carendmr" / "application" / "local_audio_lab_service.py"
WIDGET = ROOT / "carendmr" / "ui_qt" / "audio_lab_widget.py"

def test_lab_rx_wav_uses_native_output_rate():
    text = SERVICE.read_text(encoding="utf-8")
    assert 'native_rate = int(getattr(output, "_output_sample_rate", 8000) or 8000)' in text
    assert 'f"06_rx_vor_soundkarte_{rx_output_rate}hz.wav"' in text
    assert "self._write_wav(processed_path, rx_output_rate, processed)" in text

def test_lab_no_longer_labels_native_samples_as_8khz():
    text = SERVICE.read_text(encoding="utf-8")
    assert '"06_rx_vor_soundkarte_8k.wav"' not in text
    assert '"rx_before_soundcard_native"' in text
    assert '"rx_before_soundcard_hz": rx_output_rate' in text

def test_lab_records_comparable_durations():
    text = SERVICE.read_text(encoding="utf-8")
    assert '"codec_loopback": round(len(decoded) / 8000.0, 3)' in text
    assert 'len(processed) / float(rx_output_rate)' in text

def test_widget_supports_new_native_rx_metric():
    text = WIDGET.read_text(encoding="utf-8")
    assert 'levels.get("rx_before_soundcard_native", levels.get("rx_before_soundcard_8k", {}))' in text

def test_syntax():
    ast.parse(SERVICE.read_text(encoding="utf-8"))
    ast.parse(WIDGET.read_text(encoding="utf-8"))
