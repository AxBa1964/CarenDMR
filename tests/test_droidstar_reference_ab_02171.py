from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]

def test_no_stale_replay_button_reference():
    text = (ROOT / "carendmr/ui_qt/audio_lab_widget.py").read_text(encoding="utf-8")
    assert "self.replay_button" not in text

def test_md380_encoder_has_configurable_gain():
    text = (ROOT / "carendmr/encoder/md380_dynarmic.py").read_text(encoding="utf-8")
    assert "input_gain_db: float = MD380_INPUT_GAIN_DB" in text
    assert "self._input_gain" in text

def test_reference_path_is_neutral_and_zero_db():
    text = (ROOT / "carendmr/application/local_audio_lab_service.py").read_text(encoding="utf-8")
    assert "def _neutral_16k_to_8k" in text
    assert "input_gain_db=0.0" in text
    assert "03B_droidstar_referenz_vor_ambe_8k.wav" in text
    assert "05A_carendmr_md380_8k.wav" in text
    assert "05B_droidstar_referenz_md380_8k.wav" in text

def test_reference_bypasses_tuner_chain():
    text = (ROOT / "carendmr/application/local_audio_lab_service.py").read_text(encoding="utf-8")
    assert "mic_raw_16k = tuple(int(v) for v in capture._input_pcm_16k)" in text
    assert "droidstar_pcm_8k = self._neutral_16k_to_8k(mic_raw_16k)" in text

def test_ab_buttons_are_named_for_paths():
    text = (ROOT / "carendmr/ui_qt/audio_lab_widget.py").read_text(encoding="utf-8")
    assert 'QPushButton("A hören – alter CarenDMR-Pfad")' in text
    assert 'QPushButton("B hören – produktiver Referenzpfad")' in text

def test_modified_files_parse():
    for rel in (
        "carendmr/encoder/md380_dynarmic.py",
        "carendmr/application/local_audio_lab_service.py",
        "carendmr/ui_qt/audio_lab_widget.py",
    ):
        ast.parse((ROOT / rel).read_text(encoding="utf-8"))
