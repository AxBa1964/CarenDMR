from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]

def test_version():
    assert '__version__ = "0.2.1.69"' in (ROOT/"carendmr/version.py").read_text(encoding="utf-8")

def test_md380_decode_wrapper():
    text=(ROOT/"carendmr/encoder/md380_dynarmic.py").read_text(encoding="utf-8")
    assert "carendmr_md380_decode_fec.argtypes" in text
    assert "def decode_2450x1150" in text

def test_same_ambe_word_two_decoders():
    text=(ROOT/"carendmr/application/local_audio_lab_service.py").read_text(encoding="utf-8")
    assert "result_a = decoder_a.decode(word)" in text
    assert "result_b = encoder.decode_2450x1150(word)" in text
    assert "05A_md380_encode_mbelib_decode_8k.wav" in text
    assert "05B_md380_encode_md380_decode_8k.wav" in text

def test_ab_buttons():
    text=(ROOT/"carendmr/ui_qt/audio_lab_widget.py").read_text(encoding="utf-8")
    assert 'QPushButton("A hören – mbelib")' in text
    assert 'QPushButton("B hören – MD380")' in text

def test_syntax():
    for rel in (
        "carendmr/encoder/md380_dynarmic.py",
        "carendmr/application/local_audio_lab_service.py",
        "carendmr/ui_qt/audio_lab_widget.py",
    ):
        ast.parse((ROOT/rel).read_text(encoding="utf-8"))
