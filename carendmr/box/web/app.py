"""Routing und Seitenlogik der Box-Web-App (ohne Netzwerk, damit gut testbar).

``BoxWebApp.handle`` nimmt eine geparste Anfrage und liefert eine ``Response``.
Der HTTP-Server (``server.py``) ist nur die dünne Hülle darum.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from carendmr.version import __version__

from . import pages
from .auth import AdminAuth, SessionStore

SESSION_COOKIE = "carendmr_box_session"


@dataclass
class Response:
    body: str = ""
    status: int = 200
    location: str | None = None  # gesetzt → Weiterleitung (303)
    set_cookie: str | None = None
    clear_cookie: bool = False
    content_type: str = "text/html; charset=utf-8"
    download_name: str | None = None  # gesetzt → Datei-Download


@dataclass
class Request:
    method: str
    path: str
    form: dict = field(default_factory=dict)
    cookies: dict = field(default_factory=dict)


class BoxWebApp:
    """Verbindet Web-Seiten mit den Application-Diensten der Box."""

    def __init__(
        self,
        project_root: Path,
        *,
        auth: AdminAuth | None = None,
        sessions: SessionStore | None = None,
        station_factory=None,
        favorites_factory=None,
        test_login=None,
    ) -> None:
        self.project_root = Path(project_root)
        self._auth = auth or AdminAuth(self.project_root)
        self._sessions = sessions or SessionStore()
        self._station_factory = station_factory or self._default_station
        self._favorites_factory = favorites_factory or self._default_favorites
        self._test_login = test_login  # für Tests; None → echter Verbindungstest

    @staticmethod
    def _default_station(project_root: Path):
        from carendmr.application.station_settings_service import StationSettingsService

        return StationSettingsService(project_root)

    @staticmethod
    def _default_favorites(project_root: Path):
        from carendmr.box.favorites import BoxFavoritesService

        return BoxFavoritesService(project_root)

    # ------------------------------------------------------------- Routing
    def handle(self, request: Request) -> Response:
        token = request.cookies.get(SESSION_COOKIE)
        authenticated = self._sessions.is_valid(token)
        path = request.path.rstrip("/") or "/"

        if path == "/anmelden":
            return self._login(request)
        if not authenticated:
            if path == "/" and not self._auth.is_configured():
                return self._render(pages.login_page(csrf="", first_time=True))
            return self._render(pages.login_page(csrf=""))
        if path == "/abmelden":
            return self._logout(token)
        if path == "/":
            return self._overview(request)
        if path == "/station":
            return self._station(request, token)
        if path == "/talkgroups":
            return self._talkgroups(request, token)
        return self._render(pages.page("Nicht gefunden", "<p>Diese Seite gibt es nicht.</p>"), status=404)

    # ----------------------------------------------------------- Anmeldung
    def _login(self, request: Request) -> Response:
        if request.method != "POST":
            return Response(location="/")
        first_time = request.form.get("first_time") == "1"
        password = request.form.get("password", "")
        if not self._auth.is_configured() or first_time:
            if password != request.form.get("password2", ""):
                return self._render(pages.login_page("", "Die Kennwörter stimmen nicht überein.", first_time=True))
            try:
                self._auth.set_password(password)
            except ValueError as error:
                return self._render(pages.login_page("", str(error), first_time=True))
            return self._start_session()
        if self._auth.verify(password):
            return self._start_session()
        return self._render(pages.login_page("", "Falsches Kennwort."))

    def _start_session(self) -> Response:
        token = self._sessions.create()
        response = Response(location="/")
        response.set_cookie = token
        return response

    def _logout(self, token: str | None) -> Response:
        self._sessions.destroy(token)
        response = Response(location="/")
        response.clear_cookie = True
        return response

    # ------------------------------------------------------------ Seiten
    def _overview(self, request: Request) -> Response:
        station = self._station_factory(self.project_root)
        items: list[tuple[str, str]] = [("CarenDMR-Version", __version__)]
        try:
            config = station.load()
            items.append(("DMR-Station", "eingerichtet"))
            items.append(("Rufzeichen", config.callsign or "—"))
            items.append(("DMR-ID", str(config.dmr_id) if config.dmr_id else "—"))
            items.append(("Server", f"{config.host}:{config.port}"))
        except Exception:
            items.append(("DMR-Station", "noch nicht eingerichtet"))
        return self._render(pages.overview_page(items))

    def _station(self, request: Request, token: str | None) -> Response:
        station = self._station_factory(self.project_root)
        draft = station.draft()
        password_set = bool(draft.get("password"))
        csrf = self._sessions.csrf_token(token) or ""
        if request.method != "POST":
            return self._render(pages.station_page(_visible(draft), csrf, password_set=password_set))

        if not self._sessions.check_csrf(token, request.form.get("csrf")):
            return self._render(pages.station_page(
                _visible(draft), csrf, error="Sitzung abgelaufen. Bitte erneut absenden.",
                password_set=password_set,
            ))

        submitted = _read_form(request.form, draft)
        values = _visible(submitted)
        action = request.form.get("aktion", "speichern")
        try:
            config = station.build_config(**submitted)
        except ValueError as error:
            return self._render(pages.station_page(values, csrf, error=str(error),
                                                   password_set=password_set))
        if action == "test":
            try:
                message = self._run_test(config)
            except Exception as error:  # Verbindungstest meldet Klartext
                return self._render(pages.station_page(values, csrf, error=str(error),
                                                       password_set=password_set))
            return self._render(pages.station_page(values, csrf, message=message,
                                                   password_set=bool(submitted["password"])))
        try:
            station.save_station(**submitted)
        except ValueError as error:
            return self._render(pages.station_page(values, csrf, error=str(error),
                                                   password_set=password_set))
        return self._render(pages.station_page(
            _visible(station.draft()), csrf, message="Station gespeichert.",
            password_set=bool(submitted["password"]),
        ))

    def _talkgroups(self, request: Request, token: str | None) -> Response:
        from carendmr.box.favorites import BoxChannel, BoxFavoritesError, BoxFavoritesService, NETWORKS

        service = self._favorites_factory(self.project_root)
        network = request.form.get("netz", "dmr")
        if network not in NETWORKS:
            network = "dmr"
        csrf = self._sessions.csrf_token(token) or ""

        def show(error: str = "", message: str = "") -> Response:
            return self._render(pages.favorites_page(
                network, service.favorites(network), service.hotlist(network),
                csrf, error=error, message=message,
            ))

        if request.method != "POST":
            if request.form.get("export") == "1":
                response = Response(body=service.export_network(network))
                response.content_type = "application/json; charset=utf-8"
                response.download_name = f"carendmr-favoriten-{network}.json"
                return response
            return show()

        if not self._sessions.check_csrf(token, request.form.get("csrf")):
            return show(error="Sitzung abgelaufen. Bitte erneut absenden.")

        action = request.form.get("aktion", "")
        try:
            message = self._favorites_action(service, network, action, request.form)
        except BoxFavoritesError as error:
            return show(error=str(error))
        return show(message=message)

    @staticmethod
    def _favorites_action(service, network: str, action: str, form: dict) -> str:
        from carendmr.box.favorites import BoxChannel, BoxFavoritesError

        def to_int(name: str) -> int:
            raw = str(form.get(name, "")).strip()
            try:
                return int(raw)
            except ValueError as error:
                raise BoxFavoritesError(f"„{name}“ muss eine Zahl sein.") from error

        if action == "add":
            channel = BoxChannel(
                talkgroup=to_int("talkgroup"),
                name=form.get("name", ""),
                timeslot=int(form.get("timeslot", 2) or 2),
                call_type=form.get("call_type", "group"),
            )
            service.add_favorite(network, channel)
            return "Favorit hinzugefügt."
        if action == "remove":
            service.remove_favorite(network, to_int("index"))
            return "Favorit entfernt."
        if action == "up":
            service.move_favorite(network, to_int("index"), -1)
            return "Verschoben."
        if action == "down":
            service.move_favorite(network, to_int("index"), +1)
            return "Verschoben."
        if action == "assign":
            service.assign_hotlist(network, to_int("slot"), to_int("favorite"))
            return f"Auf Platz {form.get('slot')} gelegt."
        if action == "clear_slot":
            service.clear_hotlist(network, to_int("slot"))
            return f"Platz {form.get('slot')} geleert."
        if action == "import":
            added = service.import_network(
                network, form.get("import_text", ""), replace_existing=form.get("replace") == "1"
            )
            return f"{added} Favoriten geladen."
        raise BoxFavoritesError("Unbekannte Aktion.")

    def _run_test(self, config) -> str:
        if self._test_login is not None:
            return self._test_login(config)
        from carendmr.application.station_settings_service import StationSettingsService

        return StationSettingsService.test_login(config)

    # ------------------------------------------------------------ Technik
    @staticmethod
    def _render(body: str, *, status: int = 200) -> Response:
        return Response(body=body, status=status)


def _read_form(form: dict, draft: dict) -> dict:
    """Formularwerte in die Argumente von ``build_config``/``save_station``."""
    def number(name: str, fallback) -> int:
        raw = str(form.get(name, "")).strip()
        if not raw:
            return int(fallback or 0)
        try:
            return int(raw)
        except ValueError as error:
            raise ValueError(f"„{name}“ muss eine Zahl sein.") from error

    password = form.get("password", "")
    if not password:  # leer lassen = bestehendes Passwort behalten
        password = draft.get("password", "")
    return {
        "callsign": form.get("callsign", "").strip(),
        "dmr_id": number("dmr_id", draft.get("dmr_id", 0)),
        "password": password,
        "location": form.get("location", "").strip(),
        "host": form.get("host", draft.get("host", "")).strip(),
        "port": number("port", draft.get("port", 62031)),
        "latitude": float(draft.get("latitude", 0.0) or 0.0),
        "longitude": float(draft.get("longitude", 0.0) or 0.0),
    }


def _visible(values: dict) -> dict:
    """Werte fürs Formular – ohne das Passwort (wird nie angezeigt)."""
    shown = dict(values)
    shown.pop("password", None)
    shown.pop("latitude", None)
    shown.pop("longitude", None)
    return shown
