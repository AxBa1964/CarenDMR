"""0.2.1.88: Pfade für die Exe, Ersteinrichtung, Codec-Dateien, Packaging."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from carendmr import app_paths
from carendmr.application.codec_setup_service import (
    CORE_FILE,
    FIRMWARE_FILE,
    MANIFEST_FILE,
    RUNTIME_INIT_SYMBOL,
    CodecSetupError,
    CodecSetupService,
    CodecState,
)
from carendmr.application.station_settings_service import StationSettingsService
from carendmr.encoder.md380_dynarmic import default_md380_bridge_path, initialize_md380

ROOT = Path(__file__).resolve().parents[1]


# --- app_paths -------------------------------------------------------------

def test_source_start_keeps_project_directory(monkeypatch):
    monkeypatch.delenv(app_paths.DATA_DIR_ENV, raising=False)
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert app_paths.default_data_root() == ROOT
    assert app_paths.program_root() == ROOT
    assert app_paths.native_dir(ROOT) == ROOT / "native"


def test_data_dir_override(monkeypatch, tmp_path):
    monkeypatch.setenv(app_paths.DATA_DIR_ENV, str(tmp_path))
    assert app_paths.default_data_root() == tmp_path
    # Native Bibliotheken bleiben im Projekt, auch wenn Daten umgelenkt sind.
    assert app_paths.native_dir(tmp_path) == ROOT / "native"


def test_frozen_exe_uses_localappdata_and_bundle(monkeypatch, tmp_path):
    monkeypatch.delenv(app_paths.DATA_DIR_ENV, raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "bundle"), raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    if app_paths.os.name == "nt":
        assert app_paths.default_data_root() == tmp_path / "local" / "CarenDMR"
    elif sys.platform != "darwin":
        assert app_paths.default_data_root() == tmp_path / "xdg" / "CarenDMR"
    assert app_paths.program_root() == tmp_path / "bundle"
    assert app_paths.native_dir(tmp_path / "irrelevant") == tmp_path / "bundle" / "native"
    assert app_paths.tg_monitor_command(tmp_path) == [sys.executable, "--tg-monitor"]


def test_prepare_data_root_copies_seed_files_once(tmp_path):
    program = tmp_path / "program"
    (program / "config").mkdir(parents=True)
    (program / "config" / "config.json").write_text("{}", encoding="utf-8")
    (program / "config" / "talkgroups.json").write_text("[]", encoding="utf-8")
    (program / "config" / "brandmeister.example.json").write_text("{}", encoding="utf-8")
    (program / "config" / "brandmeister.local.json").write_text("geheim", encoding="utf-8")
    data = tmp_path / "data"

    copied = app_paths.prepare_data_root(data, program)
    names = sorted(path.name for path in copied)
    assert names == ["brandmeister.example.json", "config.json", "talkgroups.json"]
    # Zugangsdaten des Entwicklers werden nie kopiert.
    assert not (data / "config" / "brandmeister.local.json").exists()
    assert (data / "logs").is_dir() and (data / "data").is_dir()

    (data / "config" / "config.json").write_text('{"eigen": 1}', encoding="utf-8")
    assert app_paths.prepare_data_root(data, program) == []
    assert json.loads((data / "config" / "config.json").read_text(encoding="utf-8")) == {"eigen": 1}


def test_prepare_data_root_in_place_copies_nothing(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "config.json").write_text("{}", encoding="utf-8")
    assert app_paths.prepare_data_root(tmp_path, tmp_path) == []


def test_app_offers_tg_monitor_mode():
    from carendmr.app import _build_parser, run

    assert _build_parser().parse_args(["--tg-monitor"]).tg_monitor is True
    assert run(["--tg-monitor", "--gui"]) == 2


# --- Codec-Einrichtung -------------------------------------------------------

def _bridge(root: Path, runtime: bool) -> Path:
    path = default_md380_bridge_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = b"MZ...carendmr_md380_init..."
    if runtime:
        payload += RUNTIME_INIT_SYMBOL
    path.write_bytes(payload)
    return path


def test_codec_status_without_bridge(tmp_path):
    report = CodecSetupService(tmp_path).status()
    assert report.state is CodecState.BRIDGE_MISSING
    assert not report.ready


def test_old_bridge_needs_no_files(tmp_path):
    _bridge(tmp_path, runtime=False)
    report = CodecSetupService(tmp_path).status()
    assert report.state is CodecState.READY_EMBEDDED
    assert report.ready


def test_runtime_bridge_requires_and_installs_files(tmp_path):
    _bridge(tmp_path, runtime=True)
    service = CodecSetupService(tmp_path)
    report = service.status()
    assert report.state is CodecState.FILES_MISSING
    assert FIRMWARE_FILE in report.message and CORE_FILE in report.message

    source = tmp_path / "download"
    source.mkdir()
    firmware = source / "fw.bin"
    firmware.write_bytes(b"\x00\x40\x00\x20" + b"\x01" * 1000)
    core = source / "core.img"
    core.write_bytes(b"\x02" * 2048)

    report = service.install_files(firmware, core)
    assert report.state is CodecState.READY_FILES
    assert service.firmware_path.read_bytes() == firmware.read_bytes()
    assert service.core_path == tmp_path / "firmware" / CORE_FILE
    manifest = json.loads((tmp_path / "firmware" / MANIFEST_FILE).read_text(encoding="utf-8"))
    assert len(manifest["firmware"]["sha256"]) == 64

    assert service.remove_files().state is CodecState.FILES_MISSING


def test_wrapped_update_file_is_rejected(tmp_path):
    _bridge(tmp_path, runtime=True)
    wrapped = tmp_path / "update.bin"
    wrapped.write_bytes(b"OutSecurityBin" + b"\x00" * 300)
    core = tmp_path / "core.img"
    core.write_bytes(b"\x01")
    with pytest.raises(CodecSetupError, match="verpackte"):
        CodecSetupService(tmp_path).install_files(wrapped, core)


def test_empty_or_missing_files_are_rejected(tmp_path):
    empty = tmp_path / "empty.bin"
    empty.write_bytes(b"")
    with pytest.raises(CodecSetupError):
        CodecSetupService(tmp_path).install_files(empty, empty)
    with pytest.raises(CodecSetupError):
        CodecSetupService(tmp_path).install_files(tmp_path / "fehlt.bin", empty)


class _OldLib:
    class _Fn:
        def __init__(self, result):
            self.result = result
            self.calls = []

        def __call__(self, *args):
            self.calls.append(args)
            return self.result

    def __init__(self):
        self.carendmr_md380_init = self._Fn(0)


class _NewLib(_OldLib):
    def __init__(self):
        super().__init__()
        self.carendmr_md380_init_files = self._Fn(0)


def test_initialize_old_bridge_uses_embedded_firmware(tmp_path):
    lib = _OldLib()
    assert initialize_md380(lib, tmp_path) == 0
    assert lib.carendmr_md380_init.calls == [()]


def test_initialize_new_bridge_passes_files(tmp_path):
    lib = _NewLib()
    with pytest.raises(RuntimeError, match="nicht eingerichtet"):
        initialize_md380(lib, tmp_path)
    folder = tmp_path / "firmware"
    folder.mkdir()
    (folder / FIRMWARE_FILE).write_bytes(b"1")
    (folder / CORE_FILE).write_bytes(b"2")
    assert initialize_md380(lib, tmp_path) == 0
    (fw_arg, core_arg), = lib.carendmr_md380_init_files.calls
    assert fw_arg.endswith(FIRMWARE_FILE.encode())
    assert core_arg.endswith(CORE_FILE.encode())
    assert lib.carendmr_md380_init.calls == []


# --- Station ----------------------------------------------------------------

def test_station_setup_writes_local_config(tmp_path):
    service = StationSettingsService(tmp_path)
    assert service.needs_setup()
    draft = service.draft()
    assert draft["callsign"] == "" and draft["port"] == 62031 and draft["host"]

    with pytest.raises(ValueError):
        service.save_station(callsign="", dmr_id=2621234, password="x", host="master1.bm262.de", port=62031)
    assert service.needs_setup()

    service.save_station(callsign="dk7ee", dmr_id=2621234, password="geheim", host="master1.bm262.de", port=62031)
    assert not service.needs_setup()
    loaded = service.load()
    assert loaded.callsign == "DK7EE" and loaded.dmr_id == 2621234
    assert (tmp_path / "config" / "brandmeister.local.json").is_file()
    assert service.draft()["password"] == "geheim"


# --- Packaging und UI-Verdrahtung (Quelltextprüfung, PySide6 nicht nötig) ----

def test_packaging_files_exist_and_protect_firmware():
    spec = (ROOT / "packaging" / "CarenDMR.spec").read_text(encoding="utf-8")
    assert 'name="CarenDMR"' in spec and "console=False" in spec
    assert '"librosa"' in spec
    iss = (ROOT / "packaging" / "CarenDMR.iss").read_text(encoding="utf-8-sig")
    for token in ('Parameters: "--gui"', 'Parameters: "--easy"', 'Parameters: "--tg-monitor"', "German.isl"):
        assert token in iss
    build = (ROOT / "packaging" / "build_release.ps1").read_text(encoding="utf-8-sig")
    assert "carendmr_md380_init_files" in build
    assert "AllowEmbeddedFirmware" in build
    assert "firmware/" in (ROOT / ".gitignore").read_text(encoding="utf-8")


def test_first_run_dialogs_are_wired():
    main = (ROOT / "carendmr" / "ui_qt" / "main_window.py").read_text(encoding="utf-8")
    easy = (ROOT / "carendmr" / "ui_qt" / "easy_window.py").read_text(encoding="utf-8")
    for source in (main, easy):
        assert "run_first_run_setup(build_first_run_services(project_root))" in source
    windows = (ROOT / "carendmr" / "ui_qt" / "main_window_windows.py").read_text(encoding="utf-8")
    assert 'QAction("Sprach-Codec einrichten …", self)' in windows
    assert 'QAction("Station einrichten …", self)' in windows
    dialogs = (ROOT / "carendmr" / "ui_qt" / "first_run_dialogs.py").read_text(encoding="utf-8")
    assert dialogs.count("setBuddy") >= 1
    assert "setAccessibleName" in dialogs
