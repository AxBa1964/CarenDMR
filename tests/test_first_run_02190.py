"""0.2.1.90: Stationsvorgaben, Locator, Verbindungstest, Audio, Kontakte, Favoriten."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from carendmr import app_paths
from carendmr.application.station_settings_service import (
    STATION_DEFAULTS,
    StationSettingsService,
    locator_to_latlon,
)
from carendmr.vocoder import md380_firmware

ROOT = Path(__file__).resolve().parents[1]


def test_known_firmware_hash_is_recorded():
    assert md380_firmware.UNWRAPPED_SHA256 == (
        "c0351f250a834660641bca3b06be931c80cc1ed0ef808356c550b99cd0f4c632"
    )


def test_locator_conversion():
    assert locator_to_latlon("JO52FI") == (52.3542, 10.4583)
    assert locator_to_latlon("jo52") == (52.5, 11.0)
    with pytest.raises(ValueError):
        locator_to_latlon("XYZ")


def test_new_station_gets_fixed_defaults_and_master2(tmp_path):
    service = StationSettingsService(tmp_path)
    draft = service.draft()
    assert draft["host"] == "master2.bm262.de" and draft["port"] == 62031
    service.save_station(
        callsign="dk7ee", dmr_id=2632198, password="geheim",
        host=draft["host"], port=draft["port"],
        location="jo52fi", latitude=52.31, longitude=10.47,
    )
    data = json.loads((tmp_path / "config" / "brandmeister.local.json").read_text(encoding="utf-8"))
    for key, value in STATION_DEFAULTS.items():
        assert data[key] == value
    assert data["package_id"] == "MMDVM_MMDVM_HS_Hat"
    assert data["frequency_hz"] == 438_800_000
    assert data["location"] == "JO52FI" and data["latitude"] == 52.31


def test_existing_extra_values_are_kept(tmp_path):
    service = StationSettingsService(tmp_path)
    service.save_station(callsign="DK7EE", dmr_id=1, password="x", host="h", port=1)
    path = tmp_path / "config" / "brandmeister.local.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["description"] = "Eigene Beschreibung"
    path.write_text(json.dumps(data), encoding="utf-8")
    service.save_station(callsign="DK7EE", dmr_id=2, password="y", host="h", port=1)
    assert json.loads(path.read_text(encoding="utf-8"))["description"] == "Eigene Beschreibung"


def test_login_test_closes_client(tmp_path):
    service = StationSettingsService(tmp_path)
    config = service.build_config(callsign="DK7EE", dmr_id=1, password="x", host="h", port=1)
    calls = []

    class FakeResult:
        callsign = "DK7EE"
        host = "h"

    class FakeClient:
        def __init__(self, cfg):
            calls.append(("init", cfg.package_id))

        def login(self):
            calls.append("login")
            return FakeResult()

        def close(self):
            calls.append("close")

    message = service.test_login(config, client_factory=FakeClient)
    assert "erfolgreich" in message
    assert calls == [("init", "MMDVM_MMDVM_HS_Hat"), "login", "close"]

    class FailingClient(FakeClient):
        def login(self):
            raise RuntimeError("Das BrandMeister-Hotspot-Passwort wurde nicht bestätigt.")

    with pytest.raises(RuntimeError, match="Passwort"):
        service.test_login(config, client_factory=FailingClient)


def test_audio_setup_service_saves_and_detects(tmp_path):
    from carendmr.application.audio_setup_service import AudioSetupService
    from carendmr.audio import AudioDevice, AudioManager

    devices = [
        AudioDevice(0, "Mikro", "WASAPI", 1, 0, 48000.0, is_default_input=True),
        AudioDevice(1, "Boxen", "WASAPI", 0, 2, 48000.0, is_default_output=True),
    ]
    played = []

    class FakeBackend:
        def query_devices(self):
            return list(devices)

        def play_samples(self, samples, *, output_index, sample_rate):
            played.append((output_index, sample_rate, len(samples)))

    manager = AudioManager(FakeBackend(), tmp_path / "config" / "audio.local.json")
    service = AudioSetupService(tmp_path, manager)
    assert service.needs_setup()
    inputs, outputs = service.scan()
    assert [c.label for c in inputs] == ["Standardgerät: Mikro (WASAPI)"]
    service.play_test_tone(outputs[0].key)
    assert played and played[0][0] == 1
    service.save(inputs[0].key, outputs[0].key)
    assert not service.needs_setup()


def test_contacts_need_update_until_database_exists(tmp_path):
    from carendmr.application.contact_service import ContactService

    service = ContactService(tmp_path)
    assert service.needs_update()
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "contacts.db").write_bytes(b"x")
    assert not service.needs_update()


def test_default_favorites_are_seeded(tmp_path):
    program = tmp_path / "program"
    (program / "config").mkdir(parents=True)
    source = ROOT / "config" / "favorites.default.json"
    (program / "config" / "favorites.default.json").write_bytes(source.read_bytes())
    data = tmp_path / "data"
    app_paths.prepare_data_root(data, program)
    favorites = json.loads((data / "config" / "favorites.local.json").read_text(encoding="utf-8"))
    assert [f["target"] for f in favorites] == [91, 9990, 262, 2623]
    # In-place (Quellcode-Start) ebenfalls, aber nie überschreiben.
    app_paths.prepare_data_root(program, program)
    assert (program / "config" / "favorites.local.json").is_file()
    (program / "config" / "favorites.local.json").write_text("[]", encoding="utf-8")
    app_paths.prepare_data_root(program, program)
    assert (program / "config" / "favorites.local.json").read_text(encoding="utf-8") == "[]"


def test_ui_wiring_for_setup():
    dialogs = (ROOT / "carendmr" / "ui_qt" / "first_run_dialogs.py").read_text(encoding="utf-8")
    for token in ("class AudioSetupDialog", "class ContactsDialog", "Verbindung &testen",
                  "connection_active", "services.audio_setup.needs_setup()",
                  "services.contacts.needs_update()", 'replace(" " + SETUP_HINT, "")'):
        assert token in dialogs
    easy = (ROOT / "carendmr" / "ui_qt" / "easy_window.py").read_text(encoding="utf-8")
    for token in ('("Ctrl+Shift+S", self._open_station_setup)', '("Ctrl+Shift+C", self._open_codec_setup)',
                  '("Ctrl+Shift+A", self._open_audio_setup)', "self._offer_station_setup_after_error(value)"):
        assert token in easy
    build = (ROOT / "packaging" / "build_release.ps1").read_text(encoding="utf-8-sig")
    assert '"libstdc++-6.dll", "libgcc_s_seh-1.dll", "libwinpthread-1.dll"' in build
    spec = (ROOT / "packaging" / "CarenDMR.spec").read_text(encoding="utf-8")
    assert "favorites.default.json" in spec
