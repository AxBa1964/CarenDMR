"""0.2.1.97: Box-Web-App – Kennwort, Übersicht, DMR-Station (barrierefrei)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from carendmr.app import _build_parser
from carendmr.box.web.app import SESSION_COOKIE, BoxWebApp, Request
from carendmr.box.web.auth import AdminAuth, SessionStore
from carendmr.version import __version__


class FakeStation:
    """Ersetzt StationSettingsService – kein echtes BrandMeister."""

    def __init__(self, project_root: Path) -> None:
        self.saved: dict | None = None
        self._stored: dict = {}

    def draft(self) -> dict:
        base = {
            "callsign": "", "dmr_id": 0, "password": "", "location": "",
            "latitude": 0.0, "longitude": 0.0, "host": "master2.bm262.de", "port": 62031,
        }
        base.update(self._stored)
        return base

    def build_config(self, **values):
        if not values.get("callsign"):
            raise ValueError("Das Rufzeichen fehlt.")
        if not values.get("password"):
            raise ValueError("Das Hotspot-Passwort fehlt.")
        result = dict(values)
        result["callsign"] = result["callsign"].upper()  # wie der echte Dienst
        return result

    def save_station(self, **values):
        self.saved = self.build_config(**values)
        self._stored = dict(self.saved)

    def load(self):
        if not self._stored.get("callsign"):
            raise ValueError("nicht eingerichtet")
        from types import SimpleNamespace

        return SimpleNamespace(**self._stored)


def _app(tmp_path: Path, *, test_login=None):
    station = FakeStation(tmp_path)
    app = BoxWebApp(
        tmp_path, auth=AdminAuth(tmp_path), sessions=SessionStore(),
        station_factory=lambda _root: station, test_login=test_login,
    )
    return app, station


def _login(app, tmp_path) -> str:
    """Setzt Kennwort beim Erststart und gibt das Sitzungs-Cookie zurück."""
    response = app.handle(Request("POST", "/anmelden", {
        "first_time": "1", "password": "geheim1", "password2": "geheim1",
    }))
    assert response.location == "/" and response.set_cookie
    return response.set_cookie


def _cookies(token: str) -> dict:
    return {SESSION_COOKIE: token}


def _csrf(app, token, path="/station") -> str:
    import re

    html = app.handle(Request("GET", path, {}, _cookies(token))).body
    return re.search(r'name="csrf" value="([^"]+)"', html).group(1)


# --------------------------------------------------------------- Kennwort

def test_password_hash_is_pbkdf2_and_verifies(tmp_path):
    auth = AdminAuth(tmp_path)
    assert not auth.is_configured()
    auth.set_password("geheim1")
    record = json.loads((tmp_path / "config" / "box_admin.local.json").read_text())
    assert record["algorithm"] == "pbkdf2_sha256"
    assert "geheim1" not in json.dumps(record)
    assert auth.verify("geheim1") and not auth.verify("falsch")


def test_short_password_refused(tmp_path):
    with pytest.raises(ValueError, match="mindestens"):
        AdminAuth(tmp_path).set_password("kurz")


def test_session_expiry_and_csrf():
    clock = [0.0]
    store = SessionStore(ttl_seconds=10.0, clock=lambda: clock[0])
    token = store.create()
    assert store.is_valid(token)
    assert store.check_csrf(token, store.csrf_token(token))
    assert not store.check_csrf(token, "falsch")
    clock[0] = 20.0
    assert not store.is_valid(token)


# ------------------------------------------------------------- Anmeldung

def test_first_start_sets_password(tmp_path):
    app, _ = _app(tmp_path)
    page = app.handle(Request("GET", "/", {}, {})).body
    assert "Erststart" in page and 'lang="de"' in page
    token = _login(app, tmp_path)
    assert AdminAuth(tmp_path).is_configured()
    overview = app.handle(Request("GET", "/", {}, _cookies(token))).body
    assert "Übersicht" in overview


def test_password_mismatch_on_first_start(tmp_path):
    app, _ = _app(tmp_path)
    page = app.handle(Request("POST", "/anmelden", {
        "first_time": "1", "password": "geheim1", "password2": "anders2",
    })).body
    assert "stimmen nicht überein" in page


def test_login_required_and_wrong_password(tmp_path):
    app, _ = _app(tmp_path)
    AdminAuth(tmp_path).set_password("geheim1")
    assert "Anmelden" in app.handle(Request("GET", "/", {}, {})).body
    assert "Falsches Kennwort" in app.handle(Request("POST", "/anmelden", {"password": "falsch"})).body
    good = app.handle(Request("POST", "/anmelden", {"password": "geheim1"}))
    assert good.location == "/" and good.set_cookie


def test_logout_clears_session(tmp_path):
    app, _ = _app(tmp_path)
    token = _login(app, tmp_path)
    out = app.handle(Request("GET", "/abmelden", {}, _cookies(token)))
    assert out.clear_cookie and out.location == "/"
    assert "Anmelden" in app.handle(Request("GET", "/", {}, _cookies(token))).body


# --------------------------------------------------------------- Seiten

def test_overview_shows_version_and_station_state(tmp_path):
    app, station = _app(tmp_path)
    token = _login(app, tmp_path)
    page = app.handle(Request("GET", "/", {}, _cookies(token))).body
    assert __version__ in page and "noch nicht eingerichtet" in page
    station._stored = {"callsign": "DK7EE", "dmr_id": 2632198, "host": "master2.bm262.de", "port": 62031}
    page = app.handle(Request("GET", "/", {}, _cookies(token))).body
    assert "DK7EE" in page and "eingerichtet" in page


def test_station_save_hides_password(tmp_path):
    app, station = _app(tmp_path)
    token = _login(app, tmp_path)
    csrf = _csrf(app, token)
    response = app.handle(Request("POST", "/station", {
        "csrf": csrf, "aktion": "speichern", "callsign": "dk7ee", "dmr_id": "2632198",
        "password": "topsecret", "location": "JO52", "host": "master2.bm262.de", "port": "62031",
    }, _cookies(token)))
    assert "Station gespeichert" in response.body
    assert "topsecret" not in response.body and "gesetzt" in response.body
    assert station.saved["callsign"] == "DK7EE" and station.saved["password"] == "topsecret"


def test_station_keeps_password_when_field_empty(tmp_path):
    app, station = _app(tmp_path)
    token = _login(app, tmp_path)
    station._stored = {"callsign": "DK7EE", "dmr_id": 2632198, "password": "alt",
                       "host": "master2.bm262.de", "port": 62031}
    csrf = _csrf(app, token)
    app.handle(Request("POST", "/station", {
        "csrf": csrf, "aktion": "speichern", "callsign": "DK7EE", "dmr_id": "2632198",
        "password": "", "location": "", "host": "master2.bm262.de", "port": "62031",
    }, _cookies(token)))
    assert station.saved["password"] == "alt"


def test_station_validation_error_shown(tmp_path):
    app, _ = _app(tmp_path)
    token = _login(app, tmp_path)
    csrf = _csrf(app, token)
    page = app.handle(Request("POST", "/station", {
        "csrf": csrf, "aktion": "speichern", "callsign": "", "dmr_id": "1",
        "password": "x", "host": "h", "port": "62031",
    }, _cookies(token))).body
    assert "Rufzeichen fehlt" in page and 'role="alert"' in page


def test_station_connection_test_uses_injected_login(tmp_path):
    seen = {}

    def fake_login(config):
        seen["config"] = config
        return "Verbindungstest erfolgreich: DK7EE ist bei master2 angemeldet."

    app, _ = _app(tmp_path, test_login=fake_login)
    token = _login(app, tmp_path)
    csrf = _csrf(app, token)
    page = app.handle(Request("POST", "/station", {
        "csrf": csrf, "aktion": "test", "callsign": "DK7EE", "dmr_id": "2632198",
        "password": "topsecret", "host": "master2.bm262.de", "port": "62031",
    }, _cookies(token))).body
    assert "Verbindungstest erfolgreich" in page
    assert seen["config"]["callsign"] == "DK7EE"


def test_connection_test_error_is_shown(tmp_path):
    def failing(config):
        raise RuntimeError("Anmeldung abgelehnt: Passwort falsch.")

    app, _ = _app(tmp_path, test_login=failing)
    token = _login(app, tmp_path)
    csrf = _csrf(app, token)
    page = app.handle(Request("POST", "/station", {
        "csrf": csrf, "aktion": "test", "callsign": "DK7EE", "dmr_id": "2632198",
        "password": "x", "host": "master2.bm262.de", "port": "62031",
    }, _cookies(token))).body
    assert "Passwort falsch" in page


def test_csrf_required_for_station_post(tmp_path):
    app, station = _app(tmp_path)
    token = _login(app, tmp_path)
    page = app.handle(Request("POST", "/station", {
        "csrf": "falsch", "aktion": "speichern", "callsign": "DK7EE", "dmr_id": "1",
        "password": "x", "host": "h", "port": "62031",
    }, _cookies(token))).body
    assert "Sitzung abgelaufen" in page and station.saved is None


def test_unknown_page_is_404(tmp_path):
    app, _ = _app(tmp_path)
    token = _login(app, tmp_path)
    response = app.handle(Request("GET", "/gibtsnicht", {}, _cookies(token)))
    assert response.status == 404


def test_parser_box_web_options():
    args = _build_parser().parse_args(["--box-web", "--port", "9000"])
    assert args.box_web and args.port == 9000


def test_box_web_modules_are_qt_free():
    root = Path(__file__).resolve().parents[1] / "carendmr" / "box" / "web"
    for name in ("app.py", "auth.py", "pages.py", "server.py"):
        assert "PySide6" not in (root / name).read_text(encoding="utf-8")
