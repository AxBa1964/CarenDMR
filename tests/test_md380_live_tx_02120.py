from pathlib import Path
from carendmr.application.encoder_service import EncoderService
from carendmr.encoder.md380_dynarmic import default_md380_bridge_path

def test_md380_bridge_is_preferred_for_live_tx(tmp_path, monkeypatch):
    # Plattformpassender Bridge-Name (.dll / .dylib / .so).
    bridge = default_md380_bridge_path(tmp_path)
    bridge.parent.mkdir()
    bridge.write_bytes(b"dummy")
    service = EncoderService(tmp_path)

    class FakeMd380:
        def __init__(self, project_root, input_gain_db=None):
            self.project_root = project_root
            self.input_gain_db = input_gain_db

    monkeypatch.setattr("carendmr.application.encoder_service.Md380DynarmicEncoder", FakeMd380)
    encoder = service.create_transmit_encoder()
    assert isinstance(encoder, FakeMd380)
    assert encoder.project_root == tmp_path
    # Live-TX nutzt die MD380-Bridge ohne zusätzliche Eingangsverstärkung.
    assert encoder.input_gain_db == 0.0

def test_live_parrot_service_uses_encoder_factory():
    source = Path("carendmr/application/parrot_test_service.py").read_text(encoding="utf-8")
    assert source.count("create_transmit_encoder()") >= 2
    assert "DroidStarPluginEncoder(" not in source
