"""0.2.1.101: Box-Web System-Seite und Einrichtungsassistent."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from carendmr.box.audio_settings import BoxAudioSettings
from carendmr.box.backup import build_backup
from carendmr.box.favorites import BoxChannel, BoxFavoritesService
from carendmr.box.system_control import SystemControlError, reboot, shutdown
from carendmr.box.web.app import SESSION_COOKIE, BoxWebApp, Request
from carendmr.box.web.auth import AdminAuth, SessionStore
from carendmr.svxreflector.config import save_fm_config


# ----------------------------------------------------------- Sicherung

def test_backup_excludes_secrets(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "brandmeister.local.json").write_text(
        json.dumps({"callsign": "DK7EE", "dmr_id": 2632198, "password": "geheim"}))
    save_fm_config(tmp_path, callsign="DK7EE-TRX", auth_key="fmkey",
                   host="fm-funknetz.de", port=5308, talkgroup=20)
    BoxFavoritesService(tmp_path).add_favorite("dmr", BoxChannel(262, "D", 2, "group"))
    BoxAudioSettings(tmp_path).save(output_volume_percent=120, microphone_gain_percent=90)

    backup = build_backup(tmp_path)
    blob = json.dumps(backup)
    assert "geheim" not in blob and "fmkey" not in blob
    assert backup["station"]["callsign"] == "DK7EE" and "password" not in backup["station"]
    assert "auth_key" not in backup["fm"]
    assert backup["favorites"]["dmr"]["favorites"][0]["talkgroup"] == 262
    assert backup["audio"]["output_volume_percent"] == 120


def test_system_control_blocked_off_pi(monkeypatch):
    monkeypatch.setattr("carendmr.box.system_control.sys.platform", "win32")
    with pytest.raises(SystemControlError, match="nur auf der Box"):
        reboot()
    with pytest.raises(SystemControlError, match="nur auf der Box"):
        shutdown()


# --------------------------------------------------------------- Web

def _app(tmp_path, *, system_action=None):
    app = BoxWebApp(tmp_path, auth=AdminAuth(tmp_path), sessions=SessionStore(),
                    system_action=system_action)
    token = app.handle(Request("POST", "/anmelden", {
        "first_time": "1", "password": "geheim1", "password2": "geheim1"})).set_cookie
    return app, token


def _csrf(app, token, path="/system"):
    import re

    html = app.handle(Request("GET", path, {}, {SESSION_COOKIE: token})).body
    return re.search(r'name="csrf" value="([^"]+)"', html).group(1)


def test_change_password(tmp_path):
    app, token = _app(tmp_path)
    csrf = _csrf(app, token)
    page = app.handle(Request("POST", "/system", {
        "csrf": csrf, "aktion": "change_password", "old": "geheim1",
        "new1": "neuespw", "new2": "neuespw"}, {SESSION_COOKIE: token})).body
    assert "geändert" in page
    assert AdminAuth(tmp_path).verify("neuespw") and not AdminAuth(tmp_path).verify("geheim1")


def test_change_password_wrong_old(tmp_path):
    app, token = _app(tmp_path)
    csrf = _csrf(app, token)
    page = app.handle(Request("POST", "/system", {
        "csrf": csrf, "aktion": "change_password", "old": "falsch",
        "new1": "neuespw", "new2": "neuespw"}, {SESSION_COOKIE: token})).body
    assert "aktuelle Kennwort ist falsch" in page


def test_change_password_mismatch(tmp_path):
    app, token = _app(tmp_path)
    csrf = _csrf(app, token)
    page = app.handle(Request("POST", "/system", {
        "csrf": csrf, "aktion": "change_password", "old": "geheim1",
        "new1": "neuespw", "new2": "anders"}, {SESSION_COOKIE: token})).body
    assert "stimmen nicht überein" in page


def test_backup_download(tmp_path):
    app, token = _app(tmp_path)
    response = app.handle(Request("GET", "/system", {"backup": "1"}, {SESSION_COOKIE: token}))
    assert response.download_name == "carendmr-box-sicherung.json"
    assert json.loads(response.body)["carendmr_box_backup"] == 1


def test_reboot_uses_injected_action(tmp_path):
    seen = []
    app, token = _app(tmp_path, system_action=lambda action: seen.append(action) or "Neustart läuft.")
    csrf = _csrf(app, token)
    page = app.handle(Request("POST", "/system", {
        "csrf": csrf, "aktion": "reboot"}, {SESSION_COOKIE: token})).body
    assert seen == ["reboot"] and "Neustart läuft" in page


def test_reboot_error_shown(tmp_path):
    def failing(action):
        raise SystemControlError("nur auf der Box möglich")

    app, token = _app(tmp_path, system_action=failing)
    csrf = _csrf(app, token)
    page = app.handle(Request("POST", "/system", {
        "csrf": csrf, "aktion": "reboot"}, {SESSION_COOKIE: token})).body
    assert "nur auf der Box" in page


def test_assistant_tracks_progress(tmp_path):
    app, token = _app(tmp_path)
    page = app.handle(Request("GET", "/einrichtung", {}, {SESSION_COOKIE: token})).body
    # Kennwort ist schon gesetzt (durch Anmeldung), Rest offen.
    assert "1 von 5 Schritten erledigt" in page
    assert "Schritt 1 von 5" in page and "abbrechen" in page
    # Favorit anlegen → ein Schritt mehr erledigt.
    BoxFavoritesService(tmp_path).add_favorite("dmr", BoxChannel(262, "D", 2, "group"))
    page = app.handle(Request("GET", "/einrichtung", {}, {SESSION_COOKIE: token})).body
    assert "2 von 5 Schritten erledigt" in page


def test_system_requires_login(tmp_path):
    app = BoxWebApp(tmp_path, auth=AdminAuth(tmp_path), sessions=SessionStore())
    AdminAuth(tmp_path).set_password("geheim1")
    assert "Anmelden" in app.handle(Request("GET", "/system", {}, {})).body
    assert "Anmelden" in app.handle(Request("GET", "/einrichtung", {}, {})).body
