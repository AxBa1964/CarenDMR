from pathlib import Path

def test_md380_loader_registers_ucrt64_dll_directory():
    source = Path("carendmr/encoder/md380_dynarmic.py").read_text(encoding="utf-8")
    assert "os.add_dll_directory" in source
    assert r"C:\msys64\ucrt64\bin" in source
    assert "MD380-Dynarmic-Bridge konnte nicht geladen werden" in source
