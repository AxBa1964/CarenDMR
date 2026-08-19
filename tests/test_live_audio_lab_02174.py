from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]

def test_new_files_parse():
    for rel in (
        "carendmr/application/local_audio_lab_service.py",
        "carendmr/ui_qt/audio_lab_widget.py",
        "carendmr/ui_qt/audio_tool_windows.py",
        "carendmr/ui_qt/main_window.py",
    ):
        ast.parse((ROOT / rel).read_text(encoding="utf-8"))

def test_lab_uses_productive_audio_components():
    text = (ROOT / "carendmr/application/local_audio_lab_service.py").read_text(encoding="utf-8")
    assert "audio_service.start_live_capture" in text
    assert "encoder_service.create_transmit_encoder" in text
    assert "NativeMbeReceiveVocoder" in text
    assert "audio_service.create_pcm_output" in text
    assert "LEAD_IN_SECONDS = 0.240" in text

def test_lab_does_not_use_brandmeister():
    text = (ROOT / "carendmr/application/local_audio_lab_service.py").read_text(encoding="utf-8")
    assert "BrandMeisterClient" not in text
    assert "client.login" not in text

def test_lab_keeps_four_run_comparison():
    text = (ROOT / "carendmr/ui_qt/audio_lab_widget.py").read_text(encoding="utf-8")
    assert "Aktuell und letzte drei Durchgänge" in text
    assert "load_history(limit=4)" in text

def test_main_window_has_lab_menu_and_service():
    text = (ROOT / "carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
    assert 'QAction("Live-Audiolabor …", self)' in text
    assert "def _open_audio_lab" in text
    assert "self.local_audio_lab_service = LocalAudioLabService(" in text
    assert "self._audio_lab_window: AudioLabWindow | None = None" in text
    assert '"audio_lab": "Live-Audiolabor"' in text
