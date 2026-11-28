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
        audio_factory=None,
        test_login=None,
        fm_test=None,
        system_action=None,
    ) -> None:
        self.project_root = Path(project_root)
        self._auth = auth or AdminAuth(self.project_root)
        self._sessions = sessions or SessionStore()
        self._station_factory = station_factory or self._default_station
        self._favorites_factory = favorites_factory or self._default_favorites
        self._audio_factory = audio_factory if audio_factory is not None else self._default_audio
        self._test_login = test_login  # für Tests; None → echter Verbindungstest
        self._fm_test = fm_test
        self._system_action = system_action

    @staticmethod
    def _default_station(project_root: Path):
        from carendmr.application.station_settings_service import StationSettingsService

        return StationSettingsService(project_root)

    @staticmethod
    def _default_favorites(project_root: Path):
        from carendmr.box.favorites import BoxFavoritesService

        return BoxFavoritesService(project_root)

    @staticmethod
    def _default_audio(project_root: Path):
        from carendmr.application.audio_setup_service import AudioSetupService

        return AudioSetupService(project_root)

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
        if path == "/audio":
            return self._audio(request, token)
        if path == "/fm":
            return self._fm(request, token)
        if path == "/system":
            return self._system(request, token)
        if path == "/einrichtung":
            return self._render(pages.assistant_page(self._assistant_steps()))
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

    def _audio(self, request: Request, token: str | None) -> Response:
        from carendmr.box.audio_settings import BoxAudioSettings, BoxAudioSettingsError

        levels = BoxAudioSettings(self.project_root)
        csrf = self._sessions.csrf_token(token) or ""

        inputs: list = []
        outputs: list = []
        current_in = current_out = None
        devices_ok = True
        audio = None
        if self._audio_factory is not None:
            try:
                audio = self._audio_factory(self.project_root)
                inputs, outputs = audio.scan()
                current_in, current_out = audio.current_keys()
            except Exception:
                devices_ok = False
        else:
            devices_ok = False

        def show(error: str = "", message: str = "") -> Response:
            return self._render(pages.audio_page(
                inputs, outputs, current_in, current_out,
                levels.output_volume_percent(), levels.microphone_gain_percent(),
                csrf, error=error, message=message, devices_available=devices_ok,
            ))

        if request.method != "POST":
            return show()
        if not self._sessions.check_csrf(token, request.form.get("csrf")):
            return show(error="Sitzung abgelaufen. Bitte erneut absenden.")

        action = request.form.get("aktion", "")
        try:
            if action == "save_levels":
                levels.save(
                    output_volume_percent=request.form.get("volume", "100"),
                    microphone_gain_percent=request.form.get("gain", "100"),
                )
                return show(message="Lautstärke gespeichert.")
            if audio is None:
                return show(error="Audiogeräte sind hier nicht verfügbar.")
            if action == "save_devices":
                audio.save(request.form.get("input", ""), request.form.get("output", ""))
                current_in = request.form.get("input", "")
                current_out = request.form.get("output", "")
                return show(message="Geräte gespeichert.")
            if action == "test":
                audio.play_test_tone(request.form.get("output", ""))
                return show(message="Probeton abgespielt.")
        except (BoxAudioSettingsError, ValueError) as error:
            return show(error=str(error))
        return show(error="Unbekannte Aktion.")

    def _fm(self, request: Request, token: str | None) -> Response:
        from carendmr.svxreflector.config import FmConfigError, FmFunknetzConfig, fm_draft, save_fm_config

        draft = fm_draft(self.project_root)
        csrf = self._sessions.csrf_token(token) or ""

        def visible() -> dict:
            shown = dict(draft)
            shown.pop("key_set", None)
            return shown

        def show(error: str = "", message: str = "", values: dict | None = None) -> Response:
            return self._render(pages.fm_page(
                values if values is not None else visible(), csrf,
                error=error, message=message, key_set=draft.get("key_set", False),
            ))

        if request.method != "POST":
            return show()
        if not self._sessions.check_csrf(token, request.form.get("csrf")):
            return show(error="Sitzung abgelaufen. Bitte erneut absenden.")

        form = request.form
        values = {
            "callsign": form.get("callsign", "").strip().upper(),
            "host": form.get("host", draft["host"]).strip(),
            "software_name": form.get("software_name", "").strip() or "CarenFM",
        }
        try:
            port = int(form.get("port", draft["port"]) or draft["port"])
            talkgroup = int(form.get("talkgroup", draft["talkgroup"]) or draft["talkgroup"])
        except ValueError:
            values.update({"port": form.get("port", ""), "talkgroup": form.get("talkgroup", "")})
            return show(error="Port und Talkgroup müssen Zahlen sein.", values=values)
        values.update({"port": port, "talkgroup": talkgroup})

        action = form.get("aktion", "speichern")
        key = form.get("auth_key", "")
        try:
            if action == "test":
                effective_key = key.strip() or self._fm_stored_key()
                config = FmFunknetzConfig(
                    callsign=values["callsign"], auth_key=effective_key, host=values["host"],
                    port=port, talkgroup=talkgroup, software_name=values["software_name"],
                )
                config.validate()
                message = self._run_fm_test(config)
                return show(message=message, values=values)
            save_fm_config(
                self.project_root, callsign=values["callsign"], auth_key=key,
                host=values["host"], port=port, talkgroup=talkgroup,
                software_name=values["software_name"],
                monitor_talkgroups=tuple(draft.get("monitor_talkgroups", [])),
            )
        except (FmConfigError, ValueError) as error:
            return show(error=str(error), values=values)
        except Exception as error:  # Verbindungstest meldet Klartext
            return show(error=str(error), values=values)
        new_draft = fm_draft(self.project_root)
        return self._render(pages.fm_page(
            {k: v for k, v in new_draft.items() if k != "key_set"}, csrf,
            message="FM-Zugang gespeichert.", key_set=new_draft.get("key_set", False),
        ))

    def _system(self, request: Request, token: str | None) -> Response:
        csrf = self._sessions.csrf_token(token) or ""

        def show(error: str = "", message: str = "") -> Response:
            return self._render(pages.system_page(csrf, error=error, message=message))

        if request.method != "POST":
            if request.form.get("backup") == "1":
                from carendmr.box.backup import backup_json

                response = Response(body=backup_json(self.project_root))
                response.content_type = "application/json; charset=utf-8"
                response.download_name = "carendmr-box-sicherung.json"
                return response
            return show()
        if not self._sessions.check_csrf(token, request.form.get("csrf")):
            return show(error="Sitzung abgelaufen. Bitte erneut absenden.")

        action = request.form.get("aktion", "")
        if action == "change_password":
            if not self._auth.verify(request.form.get("old", "")):
                return show(error="Das aktuelle Kennwort ist falsch.")
            new1 = request.form.get("new1", "")
            if new1 != request.form.get("new2", ""):
                return show(error="Die neuen Kennwörter stimmen nicht überein.")
            try:
                self._auth.set_password(new1)
            except ValueError as error:
                return show(error=str(error))
            return show(message="Verwaltungskennwort geändert.")
        if action in ("reboot", "shutdown"):
            from carendmr.box.system_control import SystemControlError

            try:
                message = (self._system_action or self._default_system_action)(action)
            except SystemControlError as error:
                return show(error=str(error))
            return show(message=message)
        return show(error="Unbekannte Aktion.")

    @staticmethod
    def _default_system_action(action: str) -> str:
        from carendmr.box import system_control

        return system_control.reboot() if action == "reboot" else system_control.shutdown()

    def _assistant_steps(self) -> list[tuple[str, str, bool]]:
        return [
            ("Verwaltungskennwort", "/system", self._auth.is_configured()),
            ("DMR-Station", "/station", self._step_station_done()),
            ("Audio", "/audio", (self.project_root / "config" / "audio.local.json").is_file()),
            ("FM-Funknetz", "/fm", self._step_fm_done()),
            ("Talkgroups und Favoriten", "/talkgroups", self._step_favorites_done()),
        ]

    def _step_station_done(self) -> bool:
        try:
            return bool(self._station_factory(self.project_root).load().callsign)
        except Exception:
            return False

    def _step_fm_done(self) -> bool:
        from carendmr.svxreflector.config import fm_draft

        draft = fm_draft(self.project_root)
        return bool(draft.get("key_set")) and bool(draft.get("callsign"))

    def _step_favorites_done(self) -> bool:
        from carendmr.box.favorites import NETWORKS

        service = self._favorites_factory(self.project_root)
        return any(service.favorites(network) for network in NETWORKS)

    def _fm_stored_key(self) -> str:
        import json

        from carendmr.svxreflector.config import config_path

        path = config_path(self.project_root)
        if not path.is_file():
            return ""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return str(data.get("auth_key", "")) if isinstance(data, dict) else ""
        except (OSError, ValueError):
            return ""

    def _run_fm_test(self, config) -> str:
        if self._fm_test is not None:
            return self._fm_test(config)
        from carendmr.svxreflector.client import Connected, SvxReflectorClient

        events: list = []
        client = SvxReflectorClient(config, events.append)
        try:
            connected = client.connect()
        finally:
            client.close()
        if isinstance(connected, Connected):
            return f"Verbindungstest erfolgreich: angemeldet als {config.callsign}, Talkgroup {connected.talkgroup}."
        return "Verbindungstest erfolgreich."

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
