from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]

def test_version_02172():
    text=(ROOT/"carendmr/version.py").read_text(encoding="utf-8")
    assert '__version__ = "0.2.1.72"' in text

def test_productive_live_capture_uses_neutral_resampler():
    text=(ROOT/"carendmr/application/audio_send_service.py").read_text(encoding="utf-8")
    assert "class _NeutralDecimator16kTo8k" in text
    assert "self._resampler = _NeutralDecimator16kTo8k()" in text
    assert 'self._tx_path_name = "DroidStar-Referenz"' in text

def test_productive_tx_bypasses_old_processing():
    text=(ROOT/"carendmr/application/audio_send_service.py").read_text(encoding="utf-8")
    start=text.index("def process_mono")
    end=text.index("def on_block", start)
    body=text[start:end]
    assert "_speech_processor.process" not in body
    assert "_audio_tuner.process" not in body
    assert "mono*factor" not in body
    assert "self._resampler.process(mono)" in body

def test_productive_md380_encoder_is_zero_db():
    text=(ROOT/"carendmr/application/encoder_service.py").read_text(encoding="utf-8")
    assert "Md380DynarmicEncoder(self.project_root, input_gain_db=0.0)" in text

def test_no_stale_replay_button():
    text=(ROOT/"carendmr/ui_qt/audio_lab_widget.py").read_text(encoding="utf-8")
    assert "self.replay_button" not in text

def test_modified_files_parse():
    for rel in (
        "carendmr/application/audio_send_service.py",
        "carendmr/application/encoder_service.py",
        "carendmr/ui_qt/audio_lab_widget.py",
    ):
        ast.parse((ROOT/rel).read_text(encoding="utf-8"))
