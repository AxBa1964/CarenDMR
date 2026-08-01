"""Lokale Konfiguration für den BrandMeister-Login."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class BrandMeisterConfig:
    host: str
    port: int
    dmr_id: int
    password: str
    callsign: str
    latitude: float = 0.0
    longitude: float = 0.0
    location: str = ""
    description: str = "CarenDMR Digital Voice Client"
    frequency_hz: int = 0
    url: str = ""
    software_id: str = "20260728_CarenDMR"
    package_id: str = "MMDVM_HS_Hat"
    timeout_seconds: float = 5.0

    def validate(self) -> None:
        if not self.host.strip():
            raise ValueError("Der BrandMeister-Servername fehlt.")
        if not 1 <= self.port <= 65535:
            raise ValueError("Der UDP-Port muss zwischen 1 und 65535 liegen.")
        if not 1 <= self.dmr_id <= 0xFFFFFFFF:
            raise ValueError("Die DMR-ID muss eine positive Zahl sein.")
        if not self.password:
            raise ValueError("Das BrandMeister-Hotspot-Passwort fehlt.")
        callsign = self.callsign.strip().upper()
        if not callsign:
            raise ValueError("Das Rufzeichen fehlt.")
        if len(callsign) > 8:
            raise ValueError("Das Rufzeichen darf höchstens 8 Zeichen haben.")
        if not -90.0 <= self.latitude <= 90.0:
            raise ValueError("Der Breitengrad muss zwischen -90 und 90 liegen.")
        if not -180.0 <= self.longitude <= 180.0:
            raise ValueError("Der Längengrad muss zwischen -180 und 180 liegen.")
        if self.frequency_hz < 0 or self.frequency_hz > 999_999_999:
            raise ValueError("Die Frequenz muss zwischen 0 und 999999999 liegen.")
        if not re.fullmatch(r"\d{8}_.+", self.software_id):
            raise ValueError(
                "Die Software-ID muss dem BrandMeister-Format "
                "JJJJMMTT_Name entsprechen, zum Beispiel 20260728_CarenDMR."
            )
        if not self.package_id.startswith("MMDVM"):
            raise ValueError(
                "Die Package-ID muss für BrandMeister mit MMDVM beginnen."
            )
        if self.timeout_seconds <= 0:
            raise ValueError("Das Zeitlimit muss größer als null sein.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BrandMeisterConfig":
        config = cls(
            host=str(data["host"]),
            port=int(data.get("port", 62031)),
            dmr_id=int(data["dmr_id"]),
            password=str(data["password"]),
            callsign=str(data["callsign"]).upper(),
            latitude=float(data.get("latitude", 0.0)),
            longitude=float(data.get("longitude", 0.0)),
            location=str(data.get("location", "")),
            description=str(data.get("description", "CarenDMR Digital Voice Client")),
            frequency_hz=int(data.get("frequency_hz", 0)),
            url=str(data.get("url", "")),
            software_id=str(data.get("software_id", "20260728_CarenDMR")),
            package_id=str(data.get("package_id", "MMDVM_HS_Hat")),
            timeout_seconds=float(data.get("timeout_seconds", 5.0)),
        )
        config.validate()
        return config


class BrandMeisterConfigStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> BrandMeisterConfig:
        if not self.path.exists():
            raise ValueError(
                f"Die Datei '{self.path}' fehlt. Bitte kopieren Sie "
                "'config/brandmeister.example.json' nach "
                "'config/brandmeister.local.json' und tragen Sie Ihre Daten ein."
            )
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(
                "Die BrandMeister-Konfiguration ist nicht lesbar."
            ) from exc
        if not isinstance(data, dict):
            raise ValueError(
                "Die BrandMeister-Konfiguration muss ein JSON-Objekt sein."
            )
        try:
            return BrandMeisterConfig.from_dict(data)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"Die BrandMeister-Konfiguration ist ungültig: {exc}"
            ) from exc

    def save(self, config: BrandMeisterConfig) -> None:
        config.validate()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(config.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)
