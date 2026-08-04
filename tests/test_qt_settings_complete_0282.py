from pathlib import Path


def test_qt_settings_are_split_into_topic_tabs_and_operation_audio_is_available():
    root = Path(__file__).resolve().parents[1]
    settings = (root / "carendmr" / "ui_qt" / "settings_dialog.py").read_text(encoding="utf-8")
    main = (root / "carendmr" / "ui_qt" / "main_window.py").read_text(encoding="utf-8")
    for label in ("Audio", "Netzwerk", "Datenbanken", "Codec / Decoder", "Diagnose", "Hotkeys"):
        assert f'addTab(' in settings and f'"{label}"' in settings
    for name in ("operation_gain_slider", "operation_volume_slider", "operation_muted_check", "operation_agc_check"):
        assert name in main
    assert "ContactService" in settings
    assert "EncoderService" in settings
