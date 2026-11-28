"""0.2.1.98: Box-Favoriten je Netz mit Hotliste 1–4, Import/Export, Web-Seite."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from carendmr.box.favorites import BoxChannel, BoxFavoritesError, BoxFavoritesService
from carendmr.box.web.app import SESSION_COOKIE, BoxWebApp, Request
from carendmr.box.web.auth import AdminAuth, SessionStore


# ----------------------------------------------------------- Dienst

def test_dmr_and_fm_are_separate(tmp_path):
    service = BoxFavoritesService(tmp_path)
    service.add_favorite("dmr", BoxChannel(262, "Deutschland", timeslot=2, call_type="group"))
    service.add_favorite("fm", BoxChannel(20, "Testarea"))
    assert [f.talkgroup for f in service.favorites("dmr")] == [262]
    assert [f.talkgroup for f in service.favorites("fm")] == [20]
    # FM ignoriert Zeitschlitz/Rufart.
    assert service.favorites("fm")[0].timeslot == 0 and service.favorites("fm")[0].call_type == ""


def test_duplicate_refused(tmp_path):
    service = BoxFavoritesService(tmp_path)
    service.add_favorite("dmr", BoxChannel(262, "D", 2, "group"))
    with pytest.raises(BoxFavoritesError, match="bereits"):
        service.add_favorite("dmr", BoxChannel(262, "D2", 2, "group"))
    # Anderer Zeitschlitz ist erlaubt.
    service.add_favorite("dmr", BoxChannel(262, "D-TS1", 1, "group"))
    assert len(service.favorites("dmr")) == 2


def test_invalid_talkgroup_and_timeslot(tmp_path):
    service = BoxFavoritesService(tmp_path)
    with pytest.raises(BoxFavoritesError, match="Talkgroup"):
        service.add_favorite("dmr", BoxChannel(0, "x"))
    with pytest.raises(BoxFavoritesError, match="Zeitschlitz"):
        service.add_favorite("dmr", BoxChannel(1, "x", timeslot=3))


def test_move_and_remove(tmp_path):
    service = BoxFavoritesService(tmp_path)
    for tg in (91, 262, 2623):
        service.add_favorite("dmr", BoxChannel(tg, str(tg), 2, "group"))
    service.move_favorite("dmr", 2, -1)  # 2623 eine hoch
    assert [f.talkgroup for f in service.favorites("dmr")] == [91, 2623, 262]
    service.remove_favorite("dmr", 0)
    assert [f.talkgroup for f in service.favorites("dmr")] == [2623, 262]


def test_hotlist_assign_clear_and_persist(tmp_path):
    service = BoxFavoritesService(tmp_path)
    service.add_favorite("dmr", BoxChannel(262, "Deutschland", 2, "group"))
    service.assign_hotlist("dmr", 2, 0)
    assert service.hotlist("dmr")[1].talkgroup == 262
    assert service.hotlist("dmr")[0] is None
    # Hotliste übersteht Neuladen.
    again = BoxFavoritesService(tmp_path)
    assert again.hotlist("dmr")[1].label() == "Deutschland (262)"
    again.clear_hotlist("dmr", 2)
    assert again.hotlist("dmr")[1] is None


def test_hotlist_slot_out_of_range(tmp_path):
    service = BoxFavoritesService(tmp_path)
    service.add_favorite("dmr", BoxChannel(262, "D", 2, "group"))
    with pytest.raises(BoxFavoritesError, match="Platz"):
        service.assign_hotlist("dmr", 5, 0)


def test_export_import_roundtrip(tmp_path):
    service = BoxFavoritesService(tmp_path)
    service.add_favorite("dmr", BoxChannel(262, "Deutschland", 2, "group"))
    service.add_favorite("dmr", BoxChannel(9990, "Papagei", 2, "private"))
    service.assign_hotlist("dmr", 1, 0)
    exported = service.export_network("dmr")

    target = BoxFavoritesService(tmp_path / "andere")
    added = target.import_network("dmr", exported, replace_existing=True)
    assert added == 2
    assert [f.talkgroup for f in target.favorites("dmr")] == [262, 9990]
    assert target.favorites("dmr")[1].call_type == "private"
    assert target.hotlist("dmr")[0].talkgroup == 262


def test_import_merges_and_skips_duplicates(tmp_path):
    service = BoxFavoritesService(tmp_path)
    service.add_favorite("fm", BoxChannel(20, "Testarea"))
    added = service.import_network("fm", json.dumps([
        {"talkgroup": 20, "name": "doppelt"}, {"talkgroup": 9990, "name": "Papagei"},
    ]))
    assert added == 1
    assert [f.talkgroup for f in service.favorites("fm")] == [20, 9990]


def test_import_rejects_garbage(tmp_path):
    service = BoxFavoritesService(tmp_path)
    with pytest.raises(BoxFavoritesError, match="JSON"):
        service.import_network("dmr", "kein json")
    with pytest.raises(BoxFavoritesError, match="Favoritenliste"):
        service.import_network("dmr", json.dumps({"foo": 1}))


# ----------------------------------------------------------- Web-Seite

def _app(tmp_path):
    app = BoxWebApp(tmp_path, auth=AdminAuth(tmp_path), sessions=SessionStore(),
                    favorites_factory=lambda _r: BoxFavoritesService(tmp_path))
    response = app.handle(Request("POST", "/anmelden", {
        "first_time": "1", "password": "geheim1", "password2": "geheim1"}))
    return app, response.set_cookie


def _csrf(app, token, path):
    import re

    html = app.handle(Request("GET", path, {}, {SESSION_COOKIE: token})).body
    return re.search(r'name="csrf" value="([^"]+)"', html).group(1)


def test_page_add_and_show(tmp_path):
    app, token = _app(tmp_path)
    csrf = _csrf(app, token, "/talkgroups")
    page = app.handle(Request("POST", "/talkgroups", {
        "csrf": csrf, "netz": "dmr", "aktion": "add", "name": "Deutschland",
        "talkgroup": "262", "timeslot": "2", "call_type": "group"}, {SESSION_COOKIE: token})).body
    assert "Favorit hinzugefügt" in page and "Deutschland (262)" in page


def test_page_network_switch_to_fm(tmp_path):
    app, token = _app(tmp_path)
    page = app.handle(Request("GET", "/talkgroups", {"netz": "fm"}, {SESSION_COOKIE: token})).body
    assert "Talkgroups FM-Funknetz" in page and "zu DMR wechseln" in page


def test_page_assign_hotlist(tmp_path):
    app, token = _app(tmp_path)
    service = BoxFavoritesService(tmp_path)
    service.add_favorite("dmr", BoxChannel(262, "Deutschland", 2, "group"))
    csrf = _csrf(app, token, "/talkgroups")
    page = app.handle(Request("POST", "/talkgroups", {
        "csrf": csrf, "netz": "dmr", "aktion": "assign", "slot": "1", "favorite": "0"},
        {SESSION_COOKIE: token})).body
    assert "Auf Platz 1 gelegt" in page
    assert BoxFavoritesService(tmp_path).hotlist("dmr")[0].talkgroup == 262


def test_page_export_download(tmp_path):
    app, token = _app(tmp_path)
    BoxFavoritesService(tmp_path).add_favorite("dmr", BoxChannel(262, "D", 2, "group"))
    response = app.handle(Request("GET", "/talkgroups", {"netz": "dmr", "export": "1"},
                                  {SESSION_COOKIE: token}))
    assert response.download_name == "carendmr-favoriten-dmr.json"
    assert json.loads(response.body)["favorites"][0]["talkgroup"] == 262


def test_page_requires_login(tmp_path):
    app = BoxWebApp(tmp_path, auth=AdminAuth(tmp_path), sessions=SessionStore())
    AdminAuth(tmp_path).set_password("geheim1")
    page = app.handle(Request("GET", "/talkgroups", {}, {})).body
    assert "Anmelden" in page


def test_page_csrf_required(tmp_path):
    app, token = _app(tmp_path)
    page = app.handle(Request("POST", "/talkgroups", {
        "csrf": "falsch", "netz": "dmr", "aktion": "add", "talkgroup": "262"},
        {SESSION_COOKIE: token})).body
    assert "Sitzung abgelaufen" in page
    assert BoxFavoritesService(tmp_path).favorites("dmr") == ()


def test_import_desktop_carendmr_export(tmp_path):
    """0.2.1.102: Export des Desktop-CarenDMR (target/custom_name) laden."""
    desktop = [
        {"custom_name": "World-wide", "default_name": "World-wide", "target": 91,
         "timeslot": 2, "call_type": "group", "note": "", "position": 0},
        {"custom_name": "Papagei", "default_name": "", "target": 9990,
         "timeslot": 2, "call_type": "private", "note": "Echotest", "position": 1},
        {"custom_name": "Deutschland", "default_name": "Deutschland", "target": 262,
         "timeslot": 2, "call_type": "group", "note": "", "position": 2},
    ]
    service = BoxFavoritesService(tmp_path)
    added = service.import_network("dmr", json.dumps(desktop))
    assert added == 3
    favorites = service.favorites("dmr")
    assert [f.talkgroup for f in favorites] == [91, 9990, 262]
    assert favorites[0].name == "World-wide"
    assert favorites[1].call_type == "private"
    # default_name wird genutzt, wenn custom_name fehlt
    assert BoxChannel.from_dict({"target": 262, "default_name": "Deutschland"}).name == "Deutschland"
