"""0.2.1.91: Soundmapper-Empfehlung, Papagei privat, package_id-Korrektur,
Log-Begrenzung, Installer auf Hauptfenster, Setup-Batch, Qt-Verschlankung."""
from __future__ import annotations

import json
from pathlib import Path

from carendmr.application.channel_rules import PARROT_TARGET, required_call_type
from carendmr.brandmeister.config import BrandMeisterConfigStore
from carendmr.tg_monitor.activity_service import rotate_log

ROOT = Path(__file__).resolve().parents[1]


def test_parrot_forces_private_call():
    assert required_call_type(PARROT_TARGET, "group")[0] == "private"
    assert required_call_type(PARROT_TARGET, "group")[1]
    assert required_call_type(PARROT_TARGET, "private") == ("private", None)
    assert required_call_type(91, "group") == ("group", None)


def test_legacy_package_id_is_corrected_on_load(tmp_path):
    path = tmp_path / "brandmeister.local.json"
    path.write_text(json.dumps({
        "host": "master2.bm262.de", "port": 62031, "dmr_id": 2632198,
        "password": "x", "callsign": "DK7EE", "package_id": "MMDVM_HS_Hat",
    }), encoding="utf-8")
    config = BrandMeisterConfigStore(path).load()
    assert config.package_id == "MMDVM_MMDVM_HS_Hat"
    assert json.loads(path.read_text(encoding="utf-8"))["package_id"] == "MMDVM_MMDVM_HS_Hat"


def test_log_rotation_keeps_three_backups(tmp_path):
    log = tmp_path / "tg_monitor.log"
    for round_ in range(5):
        log.write_bytes(b"x" * 20)
        assert rotate_log(log, max_bytes=10, backups=3)
    assert not log.exists()
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "tg_monitor.log.1", "tg_monitor.log.2", "tg_monitor.log.3"
    ]
    log.write_bytes(b"x")
    assert not rotate_log(log, max_bytes=10, backups=3)


def test_soundmapper_is_recommended_and_preselected(tmp_path):
    from carendmr.application.audio_setup_service import RECOMMENDED_LABEL, AudioSetupService
    from carendmr.audio import AudioDevice, AudioManager

    devices = [
        AudioDevice(0, "Speakers (USB Audio and HID)", "MME", 0, 2, 48000.0, is_default_output=True),
        AudioDevice(1, "Microsoft Soundmapper - Output", "MME", 0, 2, 44100.0),
        AudioDevice(2, "Mikro", "MME", 1, 0, 48000.0, is_default_input=True),
        AudioDevice(3, "Microsoft Soundmapper - Input", "MME", 2, 0, 44100.0),
    ]

    class FakeBackend:
        def query_devices(self):
            return list(devices)

    service = AudioSetupService(tmp_path, AudioManager(FakeBackend(), tmp_path / "config" / "audio.local.json"))
    inputs, outputs = service.scan()
    assert inputs[0].label == RECOMMENDED_LABEL and outputs[0].label == RECOMMENDED_LABEL
    assert service.current_keys() == (inputs[0].key, outputs[0].key)


def test_installer_and_setup_batch():
    iss = (ROOT / "packaging" / "CarenDMR.iss").read_text(encoding="utf-8-sig")
    assert 'Parameters: "--gui"; Description: "CarenDMR jetzt starten"' in iss
    assert 'Name: "desktopicon_easy"' in iss
    bat = (ROOT / "build_setup.bat").read_text(encoding="ascii")
    assert "pytest tests -q" in bat and "packaging\\build_release.ps1" in bat
    build = (ROOT / "packaging" / "build_release.ps1").read_text(encoding="utf-8-sig")
    assert "check_dependencies.py" in build
    spec = (ROOT / "packaging" / "CarenDMR.spec").read_text(encoding="utf-8")
    assert '"pyside6/qml/" in dest' in spec and '"qt6quick3d"' in spec


def test_dependency_checker_reports_missing_qt(tmp_path, monkeypatch):
    import importlib.util

    spec = importlib.util.spec_from_file_location("check_dependencies", ROOT / "packaging" / "check_dependencies.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    (tmp_path / "a.dll").write_bytes(b"")
    (tmp_path / "Qt6Core.dll").write_bytes(b"")

    class Result:
        def __init__(self, text):
            self.stdout = text

    def fake_run(cmd, **_kw):
        if cmd[-1].endswith("a.dll"):
            return Result("DLL Name: Qt6Core.dll\nDLL Name: Qt6Quick.dll\nDLL Name: KERNEL32.dll\n")
        return Result("")

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    objdump = tmp_path / "objdump.exe"
    objdump.write_bytes(b"")
    assert module.check(tmp_path, objdump) == [("a.dll", "Qt6Quick.dll")]
    assert module.main(["x", str(tmp_path), str(objdump)]) == 1


def test_station_dialog_explains_locked_server_fields():
    dialogs = (ROOT / "carendmr" / "ui_qt" / "first_run_dialogs.py").read_text(encoding="utf-8")
    assert "SERVER_LOCKED_HINT" in dialogs and "setAccessibleDescription" in dialogs
    for name in ("easy_window.py", "main_window_radio.py"):
        assert "self._apply_channel_rules()" in (ROOT / "carendmr" / "ui_qt" / name).read_text(encoding="utf-8")
