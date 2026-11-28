"""Favoriten und Hotliste der CarenDMR-Box, je Netz getrennt (DMR und FM).

Eigenes, schlankes Modell in ``config/box_favorites.local.json`` – unabhängig
von den Desktop-Favoriten (`favorite_service.py`). Je Netz:
- eine Favoritenliste (feste Reihenfolge), im Web gepflegt,
- eine Hotliste mit 4 Plätzen (Tasten 1–4), jeder Platz hält eine Kopie.

Konzept: docs/CARENDMR_BOX_KONZEPT.md.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path

NETWORKS = ("dmr", "fm")
HOTLIST_SLOTS = 4
FAVORITES_FILE = "box_favorites.local.json"


class BoxFavoritesError(ValueError):
    """Ungültige Favoriten-Eingabe (Klartext für die Oberfläche)."""


@dataclass(frozen=True)
class BoxChannel:
    talkgroup: int
    name: str = ""
    timeslot: int = 2       # nur DMR
    call_type: str = "group"  # nur DMR: "group" oder "private"

    def normalized(self, network: str) -> "BoxChannel":
        if not 1 <= int(self.talkgroup) <= 0xFFFFFFFF:
            raise BoxFavoritesError("Die Talkgroup muss eine positive Zahl sein.")
        name = self.name.strip()
        if network == "fm":
            return BoxChannel(int(self.talkgroup), name, timeslot=0, call_type="")
        ts = int(self.timeslot)
        if ts not in (1, 2):
            raise BoxFavoritesError("Der Zeitschlitz muss 1 oder 2 sein.")
        call = str(self.call_type).lower()
        if call not in ("group", "private"):
            raise BoxFavoritesError("Die Rufart muss Gruppe oder privat sein.")
        return BoxChannel(int(self.talkgroup), name, ts, call)

    def key(self, network: str) -> tuple:
        if network == "fm":
            return (int(self.talkgroup),)
        return (int(self.talkgroup), int(self.timeslot), self.call_type)

    def label(self) -> str:
        return f"{self.name} ({self.talkgroup})" if self.name else str(self.talkgroup)

    def to_dict(self, network: str) -> dict:
        data = {"talkgroup": self.talkgroup, "name": self.name}
        if network == "dmr":
            data["timeslot"] = self.timeslot
            data["call_type"] = self.call_type
        return data

    @classmethod
    def from_dict(cls, item: dict) -> "BoxChannel":
        # Eigenes Box-Format (talkgroup/name) und Desktop-CarenDMR-Export
        # (target/custom_name/default_name) werden beide verstanden.
        talkgroup = item.get("talkgroup", item.get("target"))
        if talkgroup is None:
            raise KeyError("talkgroup")
        name = item.get("name") or item.get("custom_name") or item.get("default_name") or ""
        return cls(
            talkgroup=int(talkgroup),
            name=str(name),
            timeslot=int(item.get("timeslot", 2) or 2),
            call_type=str(item.get("call_type", "group") or "group"),
        )


class BoxFavoritesService:
    def __init__(self, project_root: Path) -> None:
        self._path = Path(project_root) / "config" / FAVORITES_FILE
        self._data: dict[str, dict] = {n: {"favorites": [], "hotlist": [None] * HOTLIST_SLOTS} for n in NETWORKS}
        self.load()

    # ------------------------------------------------------------- Laden
    def load(self) -> None:
        if not self._path.is_file():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(raw, dict):
            return
        for network in NETWORKS:
            section = raw.get(network, {})
            if not isinstance(section, dict):
                continue
            favorites = []
            for item in section.get("favorites", []):
                try:
                    favorites.append(BoxChannel.from_dict(item).normalized(network))
                except (BoxFavoritesError, KeyError, TypeError, ValueError):
                    continue
            hotlist: list[BoxChannel | None] = [None] * HOTLIST_SLOTS
            for index, item in enumerate(section.get("hotlist", [])[:HOTLIST_SLOTS]):
                if isinstance(item, dict):
                    try:
                        hotlist[index] = BoxChannel.from_dict(item).normalized(network)
                    except (BoxFavoritesError, KeyError, TypeError, ValueError):
                        hotlist[index] = None
            self._data[network] = {"favorites": favorites, "hotlist": hotlist}

    def _save(self) -> None:
        payload = {
            network: {
                "favorites": [c.to_dict(network) for c in self._data[network]["favorites"]],
                "hotlist": [c.to_dict(network) if c else None for c in self._data[network]["hotlist"]],
            }
            for network in NETWORKS
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(self._path)

    @staticmethod
    def _check(network: str) -> None:
        if network not in NETWORKS:
            raise BoxFavoritesError(f"Unbekanntes Netz: {network}")

    # ---------------------------------------------------------- Favoriten
    def favorites(self, network: str) -> tuple[BoxChannel, ...]:
        self._check(network)
        return tuple(self._data[network]["favorites"])

    def add_favorite(self, network: str, channel: BoxChannel) -> BoxChannel:
        self._check(network)
        normalized = channel.normalized(network)
        favorites = self._data[network]["favorites"]
        if any(fav.key(network) == normalized.key(network) for fav in favorites):
            raise BoxFavoritesError("Diese Talkgroup ist bereits in der Liste.")
        favorites.append(normalized)
        self._save()
        return normalized

    def remove_favorite(self, network: str, index: int) -> None:
        self._check(network)
        favorites = self._data[network]["favorites"]
        if not 0 <= index < len(favorites):
            raise BoxFavoritesError("Dieser Favorit ist nicht vorhanden.")
        favorites.pop(index)
        self._save()

    def move_favorite(self, network: str, index: int, delta: int) -> None:
        self._check(network)
        favorites = self._data[network]["favorites"]
        if not 0 <= index < len(favorites):
            return
        new_index = max(0, min(index + delta, len(favorites) - 1))
        if new_index == index:
            return
        favorites.insert(new_index, favorites.pop(index))
        self._save()

    # ----------------------------------------------------------- Hotliste
    def hotlist(self, network: str) -> tuple[BoxChannel | None, ...]:
        self._check(network)
        return tuple(self._data[network]["hotlist"])

    def assign_hotlist(self, network: str, slot: int, favorite_index: int) -> None:
        """Legt den Favoriten auf Hotlist-Platz (1–4) – wie „Taste lang drücken“."""
        self._check(network)
        if not 1 <= slot <= HOTLIST_SLOTS:
            raise BoxFavoritesError("Der Platz muss zwischen 1 und 4 liegen.")
        favorites = self._data[network]["favorites"]
        if not 0 <= favorite_index < len(favorites):
            raise BoxFavoritesError("Dieser Favorit ist nicht vorhanden.")
        self._data[network]["hotlist"][slot - 1] = favorites[favorite_index]
        self._save()

    def clear_hotlist(self, network: str, slot: int) -> None:
        self._check(network)
        if not 1 <= slot <= HOTLIST_SLOTS:
            raise BoxFavoritesError("Der Platz muss zwischen 1 und 4 liegen.")
        self._data[network]["hotlist"][slot - 1] = None
        self._save()

    # ------------------------------------------------------- Import/Export
    def export_network(self, network: str) -> str:
        self._check(network)
        payload = {
            "network": network,
            "favorites": [c.to_dict(network) for c in self._data[network]["favorites"]],
            "hotlist": [c.to_dict(network) if c else None for c in self._data[network]["hotlist"]],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    def import_network(self, network: str, text: str, *, replace_existing: bool = False) -> int:
        """Liest Favoriten aus JSON (Export dieser Box oder nur eine Liste)."""
        self._check(network)
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as error:
            raise BoxFavoritesError(f"Die Datei ist kein gültiges JSON: {error}") from error
        items = raw.get("favorites") if isinstance(raw, dict) else raw
        if not isinstance(items, list):
            raise BoxFavoritesError("Die Datei enthält keine Favoritenliste.")
        if replace_existing:
            self._data[network]["favorites"] = []
        favorites = self._data[network]["favorites"]
        known = {fav.key(network) for fav in favorites}
        added = 0
        for item in items:
            try:
                channel = BoxChannel.from_dict(item).normalized(network)
            except (BoxFavoritesError, KeyError, TypeError, ValueError):
                continue
            if channel.key(network) in known:
                continue
            favorites.append(channel)
            known.add(channel.key(network))
            added += 1
        if replace_existing:
            hotlist = raw.get("hotlist") if isinstance(raw, dict) else None
            if isinstance(hotlist, list):
                slots: list[BoxChannel | None] = [None] * HOTLIST_SLOTS
                for index, entry in enumerate(hotlist[:HOTLIST_SLOTS]):
                    if isinstance(entry, dict):
                        try:
                            slots[index] = BoxChannel.from_dict(entry).normalized(network)
                        except (BoxFavoritesError, KeyError, TypeError, ValueError):
                            slots[index] = None
                self._data[network]["hotlist"] = slots
        self._save()
        return added
