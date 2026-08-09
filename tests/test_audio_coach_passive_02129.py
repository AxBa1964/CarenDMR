from pathlib import Path

def test_audio_coach_does_not_start_separate_preroll_stream():
    source = Path("carendmr/application/audio_send_service.py").read_text(encoding="utf-8")
    block = source[source.index("def arm_audio_test"):source.index("def cancel_audio_test")]
    assert "_AudioTestPreRoll(self" not in block
    assert "kein separater Mikrofon-Vorlauf" in block

def test_audio_coach_uses_same_immediate_tx_release_as_normal_ptt():
    source = Path("carendmr/application/audio_send_service.py").read_text(encoding="utf-8")
    assert "signal_released = True" in source

def test_main_window_persists_geometry():
    source = Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
    assert "def _save_window_geometry" in source
    assert "def _restore_window_geometry" in source
    assert "saveGeometry()" in source
    assert "restoreGeometry(raw)" in source
    assert 'window.local.json' in source
