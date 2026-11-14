"""Stations- und Verbindungseinstellungen für Oberflächen.

Oberflächen lesen und ändern die lokale BrandMeister-Konfiguration nur über
diesen Dienst und kennen weder Dateipfade noch das BrandMeister-Paket.
"""
from __future__ import annotations

from pathlib import Path

import re

from carendmr.brandmeister.config import BrandMeisterConfig, BrandMeisterConfigStore
from carendmr.brandmeister.masters import MASTERS, BrandMeisterMaster, by_host

# Fest vorgegebene Werte für neue Stationen (ab 0.2.1.90). Diese Kombination
# wurde am 14.11.2026 erfolgreich direkt gegen master2.bm262.de getestet.
STATION_DEFAULTS = {
    "description": "CarenDMR Digital Voice Client",
    "frequency_hz": 438_800_000,
    "url": "",
    "software_id": "20260728_CarenDMR",
    "package_id": "MMDVM_MMDVM_HS_Hat",
    "timeout_seconds": 5.0,
}
DEFAULT_MASTER_HOST = "master2.bm262.de"

_LOCATOR = re.compile(r"^[A-R]{2}[0-9]{2}([A-X]{2})?$")


def locator_to_latlon(locator: str) -> tuple[float, float]:
    """Mitte eines Maidenhead-Locators (4 oder 6 Zeichen) als (Breite, Länge)."""
    text = locator.strip().upper()
    if not _LOCATOR.match(text):
        raise ValueError("Der Locator muss 4 oder 6 Zeichen haben, zum Beispiel JO52FI.")
    lon = (ord(text[0]) - ord("A")) * 20.0 - 180.0 + int(text[2]) * 2.0
    lat = (ord(text[1]) - ord("A")) * 10.0 - 90.0 + int(text[3]) * 1.0
    if len(text) == 6:
        lon += (ord(text[4]) - ord("A")) * (2.0 / 24.0) + (1.0 / 24.0)
        lat += (ord(text[5]) - ord("A")) * (1.0 / 24.0) + (0.5 / 24.0)
    else:
        lon += 1.0
        lat += 0.5
    return round(lat, 4), round(lon, 4)


class StationSettingsService:
    def __init__(self, project_root: Path) -> None:
        self._store = BrandMeisterConfigStore(Path(project_root) / "config" / "brandmeister.local.json")

    def load(self) -> BrandMeisterConfig:
        """Lädt die gespeicherte BrandMeister-Konfiguration (wirft bei Fehlern)."""
        return self._store.load()

    def station_callsign(self) -> str:
        return self.load().callsign

    @staticmethod
    def known_masters() -> tuple[BrandMeisterMaster, ...]:
        return MASTERS

    @staticmethod
    def find_master(host: str, port: int = 62031) -> BrandMeisterMaster | None:
        return by_host(host, port)

    def needs_setup(self) -> bool:
        """True, wenn keine gültige BrandMeister-Konfiguration vorliegt."""
        try:
            self._store.load()
        except ValueError:
            return True
        return False

    def draft(self) -> dict:
        """Werte für den Einrichtungsdialog (vorhandene oder Vorgaben)."""
        try:
            data = self._store.load().to_dict()
        except ValueError:
            data = {}
        default_master = next(
            (m for m in MASTERS if m.host == DEFAULT_MASTER_HOST), MASTERS[0]
        )
        return {
            "callsign": str(data.get("callsign", "")),
            "dmr_id": int(data.get("dmr_id", 0) or 0),
            "password": str(data.get("password", "")),
            "location": str(data.get("location", "")),
            "latitude": float(data.get("latitude", 0.0) or 0.0),
            "longitude": float(data.get("longitude", 0.0) or 0.0),
            "host": str(data.get("host", default_master.host)),
            "port": int(data.get("port", default_master.port)),
        }

    def build_config(
        self,
        *,
        callsign: str,
        dmr_id: int,
        password: str,
        host: str,
        port: int,
        location: str = "",
        latitude: float = 0.0,
        longitude: float = 0.0,
    ) -> BrandMeisterConfig:
        """Erzeugt eine geprüfte Konfiguration, ohne sie zu speichern.

        Bestehende Zusatzwerte bleiben erhalten; neue Stationen erhalten die
        festen Vorgaben aus ``STATION_DEFAULTS``.
        """
        try:
            data = self._store.load().to_dict()
        except ValueError:
            data = dict(STATION_DEFAULTS)
        data.update(
            {
                "callsign": callsign.strip().upper(),
                "dmr_id": int(dmr_id),
                "password": password,
                "host": host.strip(),
                "port": int(port),
                "location": location.strip().upper(),
                "latitude": float(latitude),
                "longitude": float(longitude),
            }
        )
        return BrandMeisterConfig.from_dict(data)

    def save_station(self, **values) -> None:
        """Speichert die Einrichtung; wirft ``ValueError`` mit Klartext."""
        self._store.save(self.build_config(**values))

    @staticmethod
    def test_login(config: BrandMeisterConfig, *, client_factory=None) -> str:
        """Meldet sich einmal bei BrandMeister an und wieder ab (ohne Senden).

        Liefert eine Erfolgsmeldung oder wirft eine Ausnahme mit Klartext.
        """
        from carendmr.brandmeister.client import BrandMeisterClient

        client = (client_factory or BrandMeisterClient)(config)
        result = client.login()
        try:
            return (
                f"Verbindungstest erfolgreich: {result.callsign} ist bei "
                f"{result.host} angemeldet."
            )
        finally:
            client.close()

    def save_master(self, host: str, port: int) -> None:
        """Speichert nur Server und Port; alle übrigen Werte bleiben erhalten."""
        cfg = self._store.load()
        data = cfg.to_dict()
        data["host"] = host
        data["port"] = port
        self._store.save(type(cfg).from_dict(data))
