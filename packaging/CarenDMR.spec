# -*- mode: python ; coding: utf-8 -*-
# PyInstaller-Bauplan für die Windows-Exe von CarenDMR (Ordner-Variante).
#
# Aufruf über packaging\build_release.ps1, nicht direkt.
# Ergebnis: release\dist\CarenDMR\CarenDMR.exe plus Unterordner _internal.

from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent
CONFIG = ROOT / "config"
NATIVE = ROOT / "native"

datas = [
    (str(CONFIG / "config.json"), "config"),
    (str(CONFIG / "talkgroups.json"), "config"),
    (str(CONFIG / "favorites.default.json"), "config"),
    (str(ROOT / "LICENSE"), "."),
    (str(ROOT / "README.md"), "."),
    (str(ROOT / "docs" / "UPSTREAM_PROVENANCE.md"), "docs"),
]
datas += [(str(path), "config") for path in sorted(CONFIG.glob("*.example.json"))]

# Native Bibliotheken (MD380-Bridge, MSYS2-Laufzeit-DLLs, optional mbelib).
binaries = [(str(path), "native") for path in sorted(NATIVE.glob("*.dll"))]

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    # librosa wird nur von tools/soundanalyse.py genutzt, nicht vom Programm.
    excludes=["tkinter", "librosa", "pytest", "tests", "tools"],
    noarchive=False,
)
pyz = PYZ(a.pure)

icon = ROOT / "packaging" / "CarenDMR.ico"

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CarenDMR",
    console=False,
    icon=str(icon) if icon.is_file() else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="CarenDMR",
)
