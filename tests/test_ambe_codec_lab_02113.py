from pathlib import Path
import subprocess
import sys


def test_direct_codec_lab_entrypoint_can_import_project_package():
    result = subprocess.run(
        [sys.executable, "tools/ambe_codec_lab.py", "--help"],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "03_vor_ambe_8k.wav" in result.stdout


def test_windows_build_builds_decoder_and_vocoder_bridge():
    source = Path("native/build_windows.ps1").read_text(encoding="utf-8")
    assert "carendmr_mbe.dll" in source
    assert "carendmr_vocoder_bridge.dll" in source
    assert "vocoder_plugin_bridge.cpp" in source
    assert "carendmr_vocoder_decode_2450x1150" in source
    assert "Windows-Decoder und Vocoder-Bridge erfolgreich gebaut und geprüft." in source


def test_requirements_include_pytest_for_full_suite():
    requirements = Path("requirements.txt").read_text(encoding="utf-8")
    assert "pytest" in requirements
