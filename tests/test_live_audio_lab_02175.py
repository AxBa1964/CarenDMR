from pathlib import Path
import importlib
import ast

ROOT = Path(__file__).resolve().parents[1]

def test_application_init_exports_audio_lab():
    text = (ROOT / "carendmr/application/__init__.py").read_text(encoding="utf-8")
    assert "from .local_audio_lab_service import LocalAudioLabService, AudioLabRun" in text

def test_application_init_syntax():
    ast.parse((ROOT / "carendmr/application/__init__.py").read_text(encoding="utf-8"))

def test_audio_lab_module_imports():
    module = importlib.import_module("carendmr.application.local_audio_lab_service")
    assert hasattr(module, "LocalAudioLabService")
    assert hasattr(module, "AudioLabRun")

def test_application_package_exports_symbols():
    package = importlib.import_module("carendmr.application")
    assert hasattr(package, "LocalAudioLabService")
    assert hasattr(package, "AudioLabRun")
