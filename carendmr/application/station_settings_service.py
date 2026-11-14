"""Stations- und Verbindungseinstellungen für Oberflächen.

Oberflächen lesen und ändern die lokale BrandMeister-Konfiguration nur über
diesen Dienst und kennen weder Dateipfade noch das BrandMeister-Paket.
"""
from __future__ import annotations

from pathlib import Path

from carendmr.brandmeister.config import BrandMeisterConfig, BrandMeisterConfigStore
from carendmr.brandmeister.masters import MASTERS, BrandMeisterMaster, by_host


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
        """Werte für den Ersteinrichtungsdialog (vorhandene oder leere Felder)."""
        try:
            data = self._store.load().to_dict()
        except ValueError:
            data = {}
        first = MASTERS[0]
        return {
            "callsign": str(data.get("callsign", "")),
            "dmr_id": int(data.get("dmr_id", 0) or 0),
            "password": str(data.get("password", "")),
            "host": str(data.get("host", first.host)),
            "port": int(data.get("port", first.port)),
        }

    def save_station(self, *, callsign: str, dmr_id: int, password: str, host: str, port: int) -> None:
        """Speichert die Ersteinrichtung; übrige Werte bleiben erhalten.

        Wirft ``ValueError`` mit verständlicher Meldung bei ungültigen Eingaben.
        """
        try:
            data = self._store.load().to_dict()
        except ValueError:
            data = {}
        data.update(
            {
                "callsign": callsign.strip().upper(),
                "dmr_id": int(dmr_id),
                "password": password,
                "host": host.strip(),
                "port": int(port),
            }
        )
        self._store.save(BrandMeisterConfig.from_dict(data))

    def save_master(self, host: str, port: int) -> None:
        """Speichert nur Server und Port; alle übrigen Werte bleiben erhalten."""
        cfg = self._store.load()
        data = cfg.to_dict()
        data["host"] = host
        data["port"] = port
        self._store.save(type(cfg).from_dict(data))
