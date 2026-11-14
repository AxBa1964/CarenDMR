from pathlib import Path
import subprocess
import sys


def test_md380_ab_tool_is_offline_and_has_fixed_gain():
    source = Path("tools/ambe_md380_ab.py").read_text(encoding="utf-8")
    assert "FIXED_GAIN_DB = 1.0" in source
    assert "Md380DynarmicEncoder" in source
    assert "BrandMeister" not in source
    assert "execute_live_voice_once" not in source


def test_md380_build_is_pinned():
    source = Path("native/build_md380_dynarmic_windows.ps1").read_text(encoding="utf-8")
    assert "55c9a2c6d502567380c7dfaf4a2e3cc4dd6d1dd5" in source
    assert "carendmr_md380_bridge.dll" in source


def test_tool_help_starts_from_project_root():
    result = subprocess.run([sys.executable, "tools/ambe_md380_ab.py", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "wav" in result.stdout
