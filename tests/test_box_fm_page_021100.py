"""0.2.1.100: Box-Web FM-Funknetz-Seite (Zugang speichern, Key schreibgeschützt)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from carendmr.box.web.app import SESSION_COOKIE, BoxWebApp, Request
from carendmr.box.web.auth import AdminAuth, SessionStore
from carendmr.svxreflector.config import FmConfigError, fm_draft, save_fm_config


# -------------------------------------------------------- Konfiguration

def test_fm_draft_defaults(tmp_path):
    draft = fm_draft(tmp_path)
    assert draft["host"] == "fm-funknetz.de" and draft["port"] == 5308
    assert draft["talkgroup"] == 20 and draft["software_name"] == "CarenFM"
    assert draft["key_set"] is False


def test_save_fm_and_key_preserved(tmp_path):
    save_fm_config(tmp_path, callsign="dk7ee-trx", auth_key="super-key",
                   host="fm-funknetz.de", port=5308, talkgroup=20)
    data = json.loads((tmp_path / "config" / "fm_funknetz.local.json").read_text())
    assert data["callsign"] == "DK7EE-TRX" and data["auth_key"] == "super-key"
    assert fm_draft(tmp_path)["key_set"] is True
    # Leerer Key: alter bleibt erhalten.
    save_fm_config(tmp_path, callsign="DK7EE-TRX", auth_key="", host="fm-funknetz.de",
                   port=5308, talkgroup=9990)
    data = json.loads((tmp_path / "config" / "fm_funknetz.local.json").read_text())
    assert data["auth_key"] == "super-key" and data["talkgroup"] == 9990


def test_save_fm_refuses_foreign_name(tmp_path):
    with pytest.raises(FmConfigError, match="anderes Programm"):
        save_fm_config(tmp_path, callsign="DK7EE-TRX", auth_key="k", host="fm-funknetz.de",
                       port=5308, talkgroup=20, software_name="Latry")


# --------------------------------------------------------------- Web

def _app(tmp_path, *, fm_test=None):
    app = BoxWebApp(tmp_path, auth=AdminAuth(tmp_path), sessions=SessionStore(), fm_test=fm_test)
    token = app.handle(Request("POST", "/anmelden", {
        "first_time": "1", "password": "geheim1", "password2": "geheim1"})).set_cookie
    return app, token


def _csrf(app, token):
    import re

    html = app.handle(Request("GET", "/fm", {}, {SESSION_COOKIE: token})).body
    return re.search(r'name="csrf" value="([^"]+)"', html).group(1)


def test_fm_page_shows_defaults(tmp_path):
    app, token = _app(tmp_path)
    page = app.handle(Request("GET", "/fm", {}, {SESSION_COOKIE: token})).body
    assert "FM-Funknetz" in page and "DK7EE-TRX" in page and "noch nicht gesetzt" in page


def test_fm_save_hides_key(tmp_path):
    app, token = _app(tmp_path)
    csrf = _csrf(app, token)
    page = app.handle(Request("POST", "/fm", {
        "csrf": csrf, "aktion": "speichern", "callsign": "DK7EE-TRX", "auth_key": "geheim-key",
        "software_name": "CarenFM", "host": "fm-funknetz.de", "port": "5308", "talkgroup": "20"},
        {SESSION_COOKIE: token})).body
    assert "FM-Zugang gespeichert" in page
    assert "geheim-key" not in page and "gesetzt" in page
    data = json.loads((tmp_path / "config" / "fm_funknetz.local.json").read_text())
    assert data["auth_key"] == "geheim-key"


def test_fm_connection_test_uses_injected(tmp_path):
    seen = {}

    def fake_test(config):
        seen["callsign"] = config.callsign
        return "Verbindungstest erfolgreich: angemeldet als DK7EE-TRX, Talkgroup 20."

    app, token = _app(tmp_path, fm_test=fake_test)
    # Key vorher speichern, damit der Test einen Key hat.
    save_fm_config(tmp_path, callsign="DK7EE-TRX", auth_key="k", host="fm-funknetz.de",
                   port=5308, talkgroup=20)
    csrf = _csrf(app, token)
    page = app.handle(Request("POST", "/fm", {
        "csrf": csrf, "aktion": "test", "callsign": "DK7EE-TRX", "auth_key": "",
        "software_name": "CarenFM", "host": "fm-funknetz.de", "port": "5308", "talkgroup": "20"},
        {SESSION_COOKIE: token})).body
    assert "Verbindungstest erfolgreich" in page
    assert seen["callsign"] == "DK7EE-TRX"


def test_fm_foreign_name_shown_as_error(tmp_path):
    app, token = _app(tmp_path)
    csrf = _csrf(app, token)
    page = app.handle(Request("POST", "/fm", {
        "csrf": csrf, "aktion": "speichern", "callsign": "DK7EE-TRX", "auth_key": "k",
        "software_name": "SvxLink", "host": "fm-funknetz.de", "port": "5308", "talkgroup": "20"},
        {SESSION_COOKIE: token})).body
    assert "anderes Programm" in page and 'role="alert"' in page


def test_fm_bad_port_shown(tmp_path):
    app, token = _app(tmp_path)
    csrf = _csrf(app, token)
    page = app.handle(Request("POST", "/fm", {
        "csrf": csrf, "aktion": "speichern", "callsign": "DK7EE-TRX", "auth_key": "k",
        "software_name": "CarenFM", "host": "fm-funknetz.de", "port": "abc", "talkgroup": "20"},
        {SESSION_COOKIE: token})).body
    assert "Zahlen" in page


def test_fm_page_requires_login(tmp_path):
    app = BoxWebApp(tmp_path, auth=AdminAuth(tmp_path), sessions=SessionStore())
    AdminAuth(tmp_path).set_password("geheim1")
    assert "Anmelden" in app.handle(Request("GET", "/fm", {}, {})).body
