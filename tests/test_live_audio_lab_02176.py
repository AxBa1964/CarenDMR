from pathlib import Path
import ast
import importlib

ROOT = Path(__file__).resolve().parents[1]

def test_audio_tool_windows_imports_audio_lab_widget():
    text = (ROOT / "carendmr/ui_qt/audio_tool_windows.py").read_text(encoding="utf-8")
    assert "from carendmr.ui_qt.audio_lab_widget import AudioLabWidget" in text

def test_audio_tool_windows_syntax():
    ast.parse((ROOT / "carendmr/ui_qt/audio_tool_windows.py").read_text(encoding="utf-8"))

def test_audio_tool_windows_module_imports():
    module = importlib.import_module("carendmr.ui_qt.audio_tool_windows")
    assert hasattr(module, "AudioLabWidget")
    assert hasattr(module, "AudioLabWindow")
