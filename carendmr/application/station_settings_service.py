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

    def save_master(self, host: str, port: int) -> None:
        """Speichert nur Server und Port; alle übrigen Werte bleiben erhalten."""
        cfg = self._store.load()
        data = cfg.to_dict()
        data["host"] = host
        data["port"] = port
        self._store.save(type(cfg).from_dict(data))
