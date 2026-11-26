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
# --- Nicht benötigte Qt-Bestandteile weglassen (0.2.1.91) -----------------
# CarenDMR nutzt QtCore/Gui/Widgets/Network und QtWebEngine (QRZ-Karte), aber
# kein QML, Qt Quick 3D, Charts, Multimedia usw. Die PySide6-Hooks sammeln
# diese trotzdem ein (über den QML-Ordner). Ob nach dem Filtern alle
# Abhängigkeiten vorhanden sind, prüft packaging/check_dependencies.py.
_QT_UNUSED_PREFIXES = (
    "qt63d", "qt6charts", "qt6datavisualization", "qt6graphs", "qt6labs",
    "qt6location", "qt6multimedia", "qt6quick3d", "qt6quickcontrols2",
    "qt6quickdialogs2", "qt6quickeffects", "qt6quickparticles", "qt6quickshapes",
    "qt6quicktest", "qt6quicktimeline", "qt6quickvectorimage", "qt6quicklayouts",
    "qt6remoteobjects", "qt6scxml", "qt6sensors", "qt6spatialaudio",
    "qt6statemachine", "qt6test", "qt6virtualkeyboard", "qt6shadertools",
    "qt6texttospeech", "qt6serialport", "qt6sql", "qt6webview", "qt6pdfquick",
    "qt6webenginequick", "qt6webchannelquick", "qt6qmllocalstorage",
    "qt6qmlxmllistmodel", "qt6positioningquick", "qt6sensorsquick",
    "qt6chartsqml", "qt6datavisualizationqml",
)


# Qt-Plugins, die nur die weggelassenen Module brauchen (gemeldet von
# check_dependencies.py beim ersten Bau von 0.2.1.91).
_QT_UNUSED_PLUGIN_DIRS = ("pyside6/plugins/qmltooling/",)
_QT_UNUSED_PLUGINS = ("qtvirtualkeyboardplugin", "qtposition_nmea")


def _keep(entry) -> bool:
    dest = str(entry[0]).replace("\\", "/").lower()
    if "pyside6/qml/" in dest or any(part in dest for part in _QT_UNUSED_PLUGIN_DIRS):
        return False
    name = dest.rsplit("/", 1)[-1]
    if name.startswith(_QT_UNUSED_PLUGINS):
        return False
    return not name.startswith(_QT_UNUSED_PREFIXES)


a.binaries = [entry for entry in a.binaries if _keep(entry)]
a.datas = [entry for entry in a.datas if _keep(entry)]

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
