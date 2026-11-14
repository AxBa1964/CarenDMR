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


def _fake_sources(tmp_path, monkeypatch):
    """Erzeugt Test-Firmware/RAM-Abbild und trägt deren Prüfsummen ein."""
    from carendmr.vocoder import md380_firmware as fw

    app = bytearray(b"\x00" * 0x2000)
    app[0:4] = (0x2001FFF0).to_bytes(4, "little")
    app[4:8] = (0x0800C401).to_bytes(4, "little")
    wrapped = fw.wrap(bytes(app))
    core = bytes(range(256)) * (fw.CORE_SIZE // 256)
    monkeypatch.setattr(fw, "WRAPPED_SHA256", fw.sha256(wrapped))
    monkeypatch.setattr(fw, "UNWRAPPED_SHA256", fw.sha256(fw.unwrap(wrapped)))
    monkeypatch.setattr(fw, "CORE_SHA256", fw.sha256(core))
    return bytes(app), wrapped, core


def test_runtime_bridge_requires_and_installs_files(tmp_path, monkeypatch):
    _bridge(tmp_path, runtime=True)
    service = CodecSetupService(tmp_path)
    report = service.status()
    assert report.state is CodecState.FILES_MISSING
    assert FIRMWARE_FILE in report.message and CORE_FILE in report.message

    app, wrapped, core = _fake_sources(tmp_path, monkeypatch)
    source = tmp_path / "download"
    source.mkdir()
    (source / "update.bin").write_bytes(wrapped)
    (source / "core.img").write_bytes(core)

    report = service.install_files(source / "update.bin", source / "core.img")
    assert report.state is CodecState.READY_FILES
    # Ausgepackt wird das Programmabbild (auf 512 Byte aufgefüllt).
    assert service.firmware_path.read_bytes()[: len(app)] == app
    assert service.core_path == tmp_path / "firmware" / CORE_FILE
    manifest = json.loads((tmp_path / "firmware" / MANIFEST_FILE).read_text(encoding="utf-8"))
    assert manifest["firmware"]["check"] == "verified"
    assert len(manifest["firmware"]["sha256"]) == 64

    assert service.remove_files().state is CodecState.FILES_MISSING


def test_zip_and_unwrapped_firmware_are_accepted(tmp_path, monkeypatch):
    import zipfile

    from carendmr.vocoder import md380_firmware as fw

    app, wrapped, core = _fake_sources(tmp_path, monkeypatch)
    archive = tmp_path / "fw.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr(fw.FIRMWARE_ZIP_MEMBER, wrapped)
    image, origin = fw.firmware_from_bytes(archive.read_bytes())
    assert origin == "verified" and image[: len(app)] == app
    image, origin = fw.firmware_from_bytes(app)
    assert origin == "verified" and image == app
    # 0.2.1.90: Ein ausgepacktes Abbild mit falscher Prüfsumme wird abgelehnt.
    with pytest.raises(fw.FirmwareFormatError):
        fw.firmware_from_bytes(app[:-1] + b"\x01")


def test_other_firmware_and_wrong_core_are_rejected(tmp_path, monkeypatch):
    from carendmr.vocoder import md380_firmware as fw

    _bridge(tmp_path, runtime=True)
    app, wrapped, core = _fake_sources(tmp_path, monkeypatch)
    other = fw.wrap(bytes(app) + b"\x01")
    (tmp_path / "other.bin").write_bytes(other)
    (tmp_path / "core.img").write_bytes(core)
    with pytest.raises(CodecSetupError, match="andere Firmware-Version"):
        CodecSetupService(tmp_path).install_files(tmp_path / "other.bin", tmp_path / "core.img")
    (tmp_path / "fw.bin").write_bytes(wrapped)
    (tmp_path / "bad.img").write_bytes(core[:-1] + b"\x00")
    with pytest.raises(CodecSetupError, match="RAM-Abbild"):
        CodecSetupService(tmp_path).install_files(tmp_path / "fw.bin", tmp_path / "bad.img")
    (tmp_path / "noise.bin").write_bytes(b"\x00" * 5000)
    with pytest.raises(CodecSetupError):
        CodecSetupService(tmp_path).install_files(tmp_path / "noise.bin", tmp_path / "core.img")


def test_missing_files_are_rejected(tmp_path):
    with pytest.raises(CodecSetupError):
        CodecSetupService(tmp_path).install_files(tmp_path / "fehlt.bin", tmp_path / "fehlt.img")


def test_download_uses_fixed_sources(tmp_path, monkeypatch):
    from carendmr.application import codec_setup_service as module
    from carendmr.vocoder import md380_firmware as fw

    _bridge(tmp_path, runtime=True)
    app, wrapped, core = _fake_sources(tmp_path, monkeypatch)
    calls = []

    def fake_download(url, label):
        calls.append(url)
        return wrapped if url == fw.FIRMWARE_ZIP_URL else core

    monkeypatch.setattr(module, "_download", fake_download)
    messages = []
    report = CodecSetupService(tmp_path).download_and_install(progress=messages.append)
    assert report.state is CodecState.READY_FILES
    assert calls == [fw.FIRMWARE_ZIP_URL, fw.CORE_URL]
    assert fw.FIRMWARE_ZIP_URL.startswith("https://md380.org/")
    assert len(messages) == 3


def test_unwrap_key_and_roundtrip():
    from carendmr.vocoder import md380_firmware as fw

    assert len(fw.KEY) == 1024
    assert fw.sha256(fw.KEY) == fw.KEY_SHA256
    payload = bytes(range(256)) * 9
    assert fw.unwrap(fw.wrap(payload))[: len(payload)] == payload


def test_bridge_source_loads_firmware_at_runtime():
    bridge = (ROOT / "native" / "md380_dynarmic_bridge.cpp").read_text(encoding="utf-8")
    assert 'CARENDMR_EXPORT int carendmr_md380_init_files(const char* firmware_path, const char* core_path)' in bridge
    assert "unsigned char firmware[kFirmwareCapacity];" in bridge
    cmake = (ROOT / "native" / "md380_dynarmic_build" / "CMakeLists.txt").read_text(encoding="utf-8")
    assert "add_subdirectory(" not in cmake
    assert '"${MD380_SOURCE_DIR}/md380_vocoder.cpp"' in cmake
    script = (ROOT / "native" / "build_md380_dynarmic_windows.ps1").read_text(encoding="utf-8-sig")
    assert "xxd" not in script.split("# Ab 0.2.1.89")[0]
    assert "carendmr_md380_init_files" in script


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
