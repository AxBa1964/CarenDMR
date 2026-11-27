"""Zugangsdaten für das FM-Funknetz (``config/fm_funknetz.local.json``).

Der Key steht nur in der lokalen Datei (gitignored) und wird nie ausgegeben.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_FILE = "fm_funknetz.local.json"
EXAMPLE_FILE = "fm_funknetz.example.json"
PLACEHOLDER_KEY = "KEY_VOM_NETZBETREIBER"
PLACEHOLDER_CALLSIGN = "RUFZEICHEN-APP"
DEFAULT_HOST = "fm-funknetz.de"
DEFAULT_PORT = 5308  # Port für Apps laut FUNKAMATEUR 2/26; Relais nutzen 5300
DEFAULT_TALKGROUP = 20  # „Testarea“ laut FM-Funknetz-Admin-Team
# Software-Kennung in der NodeInfo; beim FM-Funknetz als „CarenFM“ beantragt.
DEFAULT_SOFTWARE_NAME = "CarenFM"
# Fremde Programme dürfen nicht vorgetäuscht werden.
FOREIGN_SOFTWARE_NAMES = {"svxlink", "latry", "hamlink", "qsolink", "qso link", "svxconnect", "svxportal"}


class FmConfigError(ValueError):
    """Die FM-Funknetz-Konfiguration fehlt oder ist ungültig."""


@dataclass(frozen=True)
class FmFunknetzConfig:
    callsign: str
    auth_key: str = field(repr=False)
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    talkgroup: int = DEFAULT_TALKGROUP
    monitor_talkgroups: tuple[int, ...] = ()
    timeout_seconds: float = 10.0
    software_name: str = DEFAULT_SOFTWARE_NAME

    def validate(self) -> None:
        callsign = self.callsign.strip()
        if not callsign or callsign.upper() == PLACEHOLDER_CALLSIGN:
            raise FmConfigError("Das Rufzeichen für das FM-Funknetz fehlt (z. B. DK7EE-APP).")
        if len(callsign) > 20:
            raise FmConfigError("Das Rufzeichen darf höchstens 20 Zeichen haben.")
        if not self.auth_key or self.auth_key == PLACEHOLDER_KEY:
            raise FmConfigError("Der Key vom FM-Funknetz fehlt.")
        if not self.host.strip():
            raise FmConfigError("Der Server fehlt.")
        if not 1 <= self.port <= 65535:
            raise FmConfigError("Der Port muss zwischen 1 und 65535 liegen.")
        if not 1 <= self.talkgroup <= 0xFFFFFFFF:
            raise FmConfigError("Die Talkgroup muss eine positive Zahl sein.")
        if any(not 1 <= tg <= 0xFFFFFFFF for tg in self.monitor_talkgroups):
            raise FmConfigError("Mitgehörte Talkgroups müssen positive Zahlen sein.")
        name = self.software_name.strip()
        if not name or len(name) > 32:
            raise FmConfigError("Der Software-Name muss 1 bis 32 Zeichen haben.")
        if name.casefold() in FOREIGN_SOFTWARE_NAMES:
            raise FmConfigError(
                f"„{name}“ ist ein anderes Programm. CarenDMR meldet sich nur unter "
                "eigenem Namen an (z. B. CarenFM oder CarenDMR)."
            )
        if not 1.0 <= self.timeout_seconds <= 60.0:
            raise FmConfigError("Die Wartezeit muss zwischen 1 und 60 Sekunden liegen.")


def config_path(project_root: Path) -> Path:
    return Path(project_root) / "config" / CONFIG_FILE


def load_fm_config(project_root: Path) -> FmFunknetzConfig:
    path = config_path(project_root)
    if not path.is_file():
        raise FmConfigError(
            f"{CONFIG_FILE} fehlt. Vorlage {EXAMPLE_FILE} im Ordner config kopieren, "
            "in fm_funknetz.local.json umbenennen und Rufzeichen und Key eintragen."
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise FmConfigError(f"{CONFIG_FILE} ist nicht lesbar: {error}") from error
    if not isinstance(data, dict):
        raise FmConfigError(f"{CONFIG_FILE} muss ein JSON-Objekt enthalten.")
    try:
        config = FmFunknetzConfig(
            callsign=str(data.get("callsign", "")).strip().upper(),
            auth_key=str(data.get("auth_key", "")),
            host=str(data.get("host", DEFAULT_HOST)).strip(),
            port=int(data.get("port", DEFAULT_PORT)),
            talkgroup=int(data.get("talkgroup", DEFAULT_TALKGROUP)),
            monitor_talkgroups=tuple(int(tg) for tg in data.get("monitor_talkgroups", [])),
            timeout_seconds=float(data.get("timeout_seconds", 10.0)),
            software_name=str(data.get("software_name", DEFAULT_SOFTWARE_NAME)).strip(),
        )
    except (TypeError, ValueError) as error:
        raise FmConfigError(f"{CONFIG_FILE} enthält ungültige Werte: {error}") from error
    config.validate()
    return config
