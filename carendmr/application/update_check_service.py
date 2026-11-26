"""Update-Prüfung auf Anfrage (Qt-frei).

Gemeinsames Verfahren aller DK7EE-Tools: Die Programme lesen nur dann, wenn
der Nutzer „Nach Updates suchen“ wählt, die zentrale Datei
``https://dk7ee.de/download/versionen.json`` und vergleichen die Version unter
dem Schlüssel ``carendmr`` mit der eigenen. Es gibt keine automatische
Prüfung, und es wird nichts heruntergeladen oder installiert; CarenDMR
öffnet auf Wunsch nur den Download-Link oder die Projektseite im Browser.

Format der Datei: ``schema`` 1, ``tools.<schlüssel>`` mit ``name``,
``version``, ``download``, ``seite`` (Pflicht) sowie ``datum`` und ``neu``
(optional). Versionen werden Stelle für Stelle numerisch verglichen.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from carendmr.version import __version__

# Fest eingebaut; die Adresse darf sich laut Vorgabe nicht mehr ändern.
VERSIONS_URL = "https://dk7ee.de/download/versionen.json"
TOOL_KEY = "carendmr"
SUPPORTED_SCHEMA = 1
TIMEOUT_SECONDS = 10
MAX_BYTES = 256 * 1024

_VERSION = re.compile(r"^\d+(\.\d+){1,3}$")


class UpdateState(str, Enum):
    CURRENT = "current"
    AVAILABLE = "available"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class UpdateResult:
    state: UpdateState
    message: str
    current: str
    latest: str = ""
    date: str = ""
    news: str = ""
    download: str = ""
    page: str = ""


def parse_version(text: str) -> tuple[int, ...]:
    value = str(text).strip()
    if not _VERSION.match(value):
        raise ValueError(f"Ungültige Versionsnummer: {value!r}")
    parts = [int(part) for part in value.split(".")]
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts)


def _https_or_empty(value: object) -> str:
    text = str(value or "").strip()
    return text if text.lower().startswith("https://") else ""


def _fetch(url: str) -> bytes:
    import ssl
    import urllib.request

    try:
        import certifi

        context = ssl.create_default_context(cafile=certifi.where())
    except ImportError:  # pragma: no cover - certifi steht in requirements.txt
        context = ssl.create_default_context()
    request = urllib.request.Request(
        url, headers={"User-Agent": f"CarenDMR/{__version__}", "Cache-Control": "no-cache"}
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS, context=context) as response:
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("Die Versionsdatei ist unerwartet groß.")
    return data


def evaluate(raw: bytes, current: str = __version__) -> UpdateResult:
    """Wertet den Inhalt von versionen.json aus (ohne Netzwerk, gut testbar)."""
    def error(text: str) -> UpdateResult:
        return UpdateResult(UpdateState.ERROR, text, current)

    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return error("Die Versionsdatei ist nicht lesbar. Bitte später erneut versuchen.")
    if not isinstance(data, dict) or data.get("schema") != SUPPORTED_SCHEMA:
        return error("Die Versionsdatei hat ein unbekanntes Format.")
    entry = (data.get("tools") or {}).get(TOOL_KEY)
    if not isinstance(entry, dict):
        return error("In der Versionsdatei ist CarenDMR nicht eingetragen.")
    try:
        latest = str(entry["version"]).strip()
        newer = parse_version(latest) > parse_version(current)
    except (KeyError, ValueError):
        return error("Die Versionsangabe für CarenDMR ist ungültig.")

    download = _https_or_empty(entry.get("download"))
    page = _https_or_empty(entry.get("seite"))
    date = str(entry.get("datum") or "").strip()
    news = str(entry.get("neu") or "").strip()
    if not newer:
        return UpdateResult(
            UpdateState.CURRENT,
            f"Sie haben die aktuelle Version {current}.",
            current, latest, date, news, download, page,
        )
    text = f"Version {latest}" + (f" vom {date}" if date else "") + " ist verfügbar."
    text += f" Installiert ist {current}."
    if news:
        text += f" Neu: {news}"
    return UpdateResult(UpdateState.AVAILABLE, text, current, latest, date, news, download, page)


class UpdateCheckService:
    def __init__(self, fetch: Callable[[str], bytes] | None = None, current: str = __version__) -> None:
        self._fetch = fetch or _fetch
        self.current = current

    def check(self) -> UpdateResult:
        try:
            raw = self._fetch(VERSIONS_URL)
        except Exception as error:  # Netzwerkfehler aller Art
            return UpdateResult(
                UpdateState.ERROR,
                "Die Update-Prüfung ist gerade nicht möglich (keine Verbindung zu dk7ee.de). "
                f"CarenDMR läuft normal weiter. Technische Meldung: {error}",
                self.current,
            )
        return evaluate(raw, self.current)
