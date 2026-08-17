from pathlib import Path


def test_qt_0283_operational_controls_and_feedback():
    root = Path(__file__).resolve().parents[1]
    main = (root / "carendmr" / "ui_qt" / "main_window.py").read_text(encoding="utf-8")
    settings = (root / "carendmr" / "ui_qt" / "settings_dialog.py").read_text(encoding="utf-8")
    encoder = (root / "carendmr" / "application" / "encoder_service.py").read_text(encoding="utf-8")
    assert "operation_volume_slider.setRange(0, 100)" in main
    assert "Kontaktdaten werden aktualisiert … Bitte warten." in settings
    assert "vocoder_plugin*" in settings
    assert "discover_plugin_candidates" in encoder
    assert "vocoder_plugin.winnt.x86_64" in encoder
