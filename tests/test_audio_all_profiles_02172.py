from pathlib import Path
import ast
ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "audio_path_regression.py"

def test_all_profiles_is_default():
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'choices=("all", "current", "Neutral", "Klar", "DX", "Warm")' in text
    assert 'default="all"' in text
    assert '("Neutral", "Klar", "DX", "Warm") if args.profile == "all"' in text

def test_outputs_profile_comparison():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "profile_comparison.json" in text
    assert "profile_comparison.txt" in text
    assert "results_all_profiles.json" in text

def test_keeps_audio_instrumentation_fix():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "service.set_audio_debug_wav_enabled(True)" in text
    assert "Audio-QS-Instrumentierung leer" in text

def test_syntax():
    ast.parse(SCRIPT.read_text(encoding="utf-8"))
