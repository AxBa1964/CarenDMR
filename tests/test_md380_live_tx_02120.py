from pathlib import Path
from carendmr.application.encoder_service import EncoderService

def test_md380_bridge_is_preferred_for_live_tx(tmp_path, monkeypatch):
    native = tmp_path / "native"
    native.mkdir()
    bridge = native / "carendmr_md380_bridge.dll"
    bridge.write_bytes(b"dummy")
    service = EncoderService(tmp_path)

    class FakeMd380:
        def __init__(self, project_root):
            self.project_root = project_root

    monkeypatch.setattr("carendmr.application.encoder_service.Md380DynarmicEncoder", FakeMd380)
    encoder = service.create_transmit_encoder()
    assert isinstance(encoder, FakeMd380)
    assert encoder.project_root == tmp_path

def test_live_parrot_service_uses_encoder_factory():
    source = Path("carendmr/application/parrot_test_service.py").read_text(encoding="utf-8")
    assert source.count("create_transmit_encoder()") >= 2
    assert "DroidStarPluginEncoder(" not in source
