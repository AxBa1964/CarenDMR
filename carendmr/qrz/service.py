"""QRZ.com XML Callbook integration, independent from the DMR core."""
from __future__ import annotations

import json
import threading
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

QRZ_XML_URL = "https://xmldata.qrz.com/xml/current/"
DEFAULT_TIMEOUT_SECONDS = 10.0


class QrzServiceError(RuntimeError):
    pass


class QrzNotFound(QrzServiceError):
    pass


@dataclass(frozen=True, slots=True)
class QrzConfig:
    username: str
    password: str
    own_callsign: str = ""
    maptiler_api_key: str = ""

    @classmethod
    def load(cls, path: Path) -> "QrzConfig":
        path = Path(path)
        if not path.is_file():
            raise QrzServiceError(
                "QRZ.com ist noch nicht eingerichtet. "
                "Bitte config/qrz.example.json nach config/qrz.local.json kopieren."
            )
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise QrzServiceError("config/qrz.local.json ist nicht lesbar.") from error
        username = str(data.get("username", "")).strip()
        password = str(data.get("password", ""))
        own_callsign = str(data.get("own_callsign", username)).strip().upper()
        maptiler_api_key = str(data.get("maptiler_api_key", "")).strip()
        if not username or not password:
            raise QrzServiceError("QRZ.com Benutzername oder Passwort fehlt.")
        return cls(
            username=username,
            password=password,
            own_callsign=own_callsign,
            maptiler_api_key=maptiler_api_key,
        )


@dataclass(frozen=True, slots=True)
class QrzProfile:
    callsign: str
    first_name: str = ""
    last_name: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    grid: str = ""
    latitude: float | None = None
    longitude: float | None = None
    image_url: str = ""
    web_url: str = ""
    email: str = ""
    cq_zone: str = ""
    itu_zone: str = ""
    qsl_manager: str = ""
    lotw: str = ""
    eqsl: str = ""
    biography_size: str = ""

    @property
    def display_name(self) -> str:
        return " ".join(part for part in (self.first_name, self.last_name) if part).strip()

    @property
    def location_text(self) -> str:
        return ", ".join(part for part in (self.city, self.state, self.country) if part).strip()

    @property
    def qrz_page_url(self) -> str:
        return self.web_url or f"https://www.qrz.com/db/{self.callsign}"


def _text(node: ET.Element, name: str) -> str:
    child = node.find(f"./{{*}}{name}")
    if child is None or child.text is None:
        return ""
    return child.text.strip()


def _float_or_none(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_callsign_profile(xml_bytes: bytes) -> QrzProfile:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as error:
        raise QrzServiceError("QRZ.com lieferte ungültiges XML.") from error

    callsign = root.find(".//{*}Callsign")
    if callsign is None:
        error_text = ""
        session = root.find(".//{*}Session")
        if session is not None:
            error_text = _text(session, "Error") or _text(session, "Message")
        if "not found" in error_text.lower():
            raise QrzNotFound(error_text or "Rufzeichen bei QRZ.com nicht gefunden.")
        raise QrzServiceError(error_text or "QRZ.com lieferte keinen Rufzeichendatensatz.")

    call = _text(callsign, "call").upper()
    if not call:
        raise QrzServiceError("QRZ.com lieferte einen Datensatz ohne Rufzeichen.")

    return QrzProfile(
        callsign=call,
        first_name=_text(callsign, "fname"),
        last_name=_text(callsign, "name"),
        city=_text(callsign, "addr2"),
        state=_text(callsign, "state"),
        country=_text(callsign, "country") or _text(callsign, "land"),
        grid=_text(callsign, "grid"),
        latitude=_float_or_none(_text(callsign, "lat")),
        longitude=_float_or_none(_text(callsign, "lon")),
        image_url=_text(callsign, "image"),
        web_url=_text(callsign, "url"),
        email=_text(callsign, "email"),
        cq_zone=_text(callsign, "cqzone"),
        itu_zone=_text(callsign, "ituzone"),
        qsl_manager=_text(callsign, "qslmgr"),
        lotw=_text(callsign, "lotw"),
        eqsl=_text(callsign, "eqsl"),
        biography_size=_text(callsign, "bio"),
    )


class QrzLookupService:
    """Session-key aware QRZ XML client with a small in-memory cache."""

    def __init__(self, config_path: Path, *, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        self.config_path = Path(config_path)
        self.timeout_seconds = float(timeout_seconds)
        self._lock = threading.RLock()
        self._session_key = ""
        self._config: QrzConfig | None = None
        self._cache: dict[str, QrzProfile | None] = {}

    @property
    def maptiler_api_key(self) -> str:
        try:
            return self._load_config().maptiler_api_key
        except QrzServiceError:
            return ""

    @property
    def configured(self) -> bool:
        try:
            self._load_config()
            return True
        except QrzServiceError:
            return False

    def _load_config(self) -> QrzConfig:
        with self._lock:
            if self._config is None:
                self._config = QrzConfig.load(self.config_path)
            return self._config

    def _post(self, parameters: dict[str, str]) -> bytes:
        body = urlencode(parameters).encode("utf-8")
        request = Request(
            QRZ_XML_URL,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "CarenDMR-QRZ/0.2",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            raise QrzServiceError(f"QRZ.com ist nicht erreichbar: {error}") from error

    @staticmethod
    def _session_info(xml_bytes: bytes) -> tuple[str, str]:
        try:
            root = ET.fromstring(xml_bytes)
        except ET.ParseError as error:
            raise QrzServiceError("QRZ.com lieferte ungültiges XML.") from error
        session = root.find(".//{*}Session")
        if session is None:
            return "", "QRZ.com lieferte keine Sitzungsinformationen."
        key = _text(session, "Key")
        error_text = _text(session, "Error") or _text(session, "Message")
        return key, error_text

    def _login(self) -> str:
        config = self._load_config()
        xml_bytes = self._post({
            "username": config.username,
            "password": config.password,
            "agent": "CarenDMR-0.2",
        })
        key, error_text = self._session_info(xml_bytes)
        if not key:
            raise QrzServiceError(error_text or "QRZ.com Anmeldung fehlgeschlagen.")
        self._session_key = key
        return key

    @staticmethod
    def _session_error(xml_bytes: bytes) -> str:
        try:
            root = ET.fromstring(xml_bytes)
        except ET.ParseError:
            return ""
        session = root.find(".//{*}Session")
        return (_text(session, "Error") if session is not None else "").strip()

    def lookup(self, callsign: str, *, use_cache: bool = True) -> QrzProfile:
        normalized = str(callsign).strip().upper()
        if not normalized:
            raise QrzNotFound("Kein Rufzeichen angegeben.")

        with self._lock:
            if use_cache and normalized in self._cache:
                cached = self._cache[normalized]
                if cached is None:
                    raise QrzNotFound(f"{normalized} ist bei QRZ.com nicht vorhanden.")
                return cached

            key = self._session_key or self._login()
            xml_bytes = self._post({"s": key, "callsign": normalized})
            session_error = self._session_error(xml_bytes)
            if session_error and any(
                marker in session_error.lower()
                for marker in ("session", "timeout", "key")
            ):
                self._session_key = ""
                key = self._login()
                xml_bytes = self._post({"s": key, "callsign": normalized})

            try:
                profile = parse_callsign_profile(xml_bytes)
            except QrzNotFound:
                self._cache[normalized] = None
                raise

            self._cache[normalized] = profile
            return profile

    def lookup_own_station(self) -> QrzProfile | None:
        config = self._load_config()
        if not config.own_callsign:
            return None
        try:
            return self.lookup(config.own_callsign)
        except QrzNotFound:
            return None
