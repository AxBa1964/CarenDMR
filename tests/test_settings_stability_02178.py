from pathlib import Path

from carendmr.application.encoder_service import EncoderService


def test_passive_md380_diagnostics_do_not_create_encoder(tmp_path, monkeypatch):
    native = tmp_path / "native"
    native.mkdir()
    for name in ("carendmr_md380_bridge.dll", "libcarendmr_md380_bridge.so", "libcarendmr_md380_bridge.dylib"):
        (native / name).write_bytes(b"placeholder")
    service = EncoderService(tmp_path)

    def fail_create():
        raise AssertionError("native encoder must not be created for passive settings diagnostics")

    monkeypatch.setattr(service, "create_transmit_encoder", fail_create)
    diag = service.configured_diagnostics()

    assert diag.ready is True
    assert diag.backend == "MD380/Dynarmic"
    assert diag.encoded_bytes == 0
    assert "Keine erneute JIT-Probecodierung" in diag.message


def test_connection_button_width_allows_long_connecting_text():
    theme = Path(__file__).parents[1] / "carendmr" / "ui_qt" / "theme.py"
    text = theme.read_text(encoding="utf-8")
    assert "connection_control_width: int = 220" in text
