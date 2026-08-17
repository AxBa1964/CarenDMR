import subprocess
import sys


def test_native_vocoder_import_has_no_package_cycle():
    result = subprocess.run(
        [sys.executable, "-c", "from carendmr.vocoder.native import NativeMbeReceiveVocoder; print('OK')"],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_brandmeister_and_vocoder_can_be_imported_together():
    result = subprocess.run(
        [sys.executable, "-c", "import carendmr.brandmeister; import carendmr.vocoder; print('OK')"],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
