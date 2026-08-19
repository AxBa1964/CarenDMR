from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]

def test_version():
    text=(ROOT/"carendmr/version.py").read_text(encoding="utf-8")
    assert '__version__ = "0.2.1.70"' in text

def test_productive_receive_uses_md380():
    text=(ROOT/"carendmr/application/receive_service.py").read_text(encoding="utf-8")
    assert "Md380DynarmicReceiveVocoder" in text
    assert "decoder_factory=lambda: Md380DynarmicReceiveVocoder(self.project_root)" in text

def test_rx_100_percent_is_unity_gain():
    text=(ROOT/"carendmr/audio/pcm_output.py").read_text(encoding="utf-8")
    assert "base_gain = 1.0" in text
    assert "base_gain = 4.0" not in text

def test_md380_receive_wrapper_exists():
    text=(ROOT/"carendmr/vocoder/md380_dynarmic.py").read_text(encoding="utf-8")
    assert "class Md380DynarmicReceiveVocoder" in text
    assert "carendmr_md380_decode_fec" in text

def test_lab_b_uses_productive_md380_receive_decoder():
    text=(ROOT/"carendmr/application/local_audio_lab_service.py").read_text(encoding="utf-8")
    assert "decoder_b = Md380DynarmicReceiveVocoder(self.project_root)" in text
    assert "result_b = decoder_b.decode(word)" in text

def test_modified_files_parse():
    for rel in (
        "carendmr/vocoder/md380_dynarmic.py",
        "carendmr/vocoder/__init__.py",
        "carendmr/application/receive_service.py",
        "carendmr/audio/pcm_output.py",
        "carendmr/application/local_audio_lab_service.py",
    ):
        ast.parse((ROOT/rel).read_text(encoding="utf-8"))


def test_pcm_callback_preserves_samples_at_100_percent_agc_off():
    import importlib.util
    import struct
    module_path = ROOT / "carendmr/audio/pcm_output.py"
    spec = importlib.util.spec_from_file_location("pcm_output_02170", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    output = module.BufferedPcmOutput(
        sample_rate=8000,
        output_sample_rate=8000,
        volume=lambda: 1.0,
        agc_enabled=lambda: False,
    )
    values = (-30000, -12000, -1, 0, 1, 12000, 30000)
    output.write(values)
    raw = bytearray(len(values) * 2)
    output._callback(memoryview(raw), len(values), None, None)
    assert struct.unpack(f"<{len(values)}h", raw) == values
