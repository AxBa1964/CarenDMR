"""Persistenz, Sortierung sowie Import/Export persönlicher DMR-Favoriten."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from carendmr.domain import FavoriteChannel


class FavoriteService:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._favorites: list[FavoriteChannel] = []
        self.load()

    @property
    def favorites(self) -> tuple[FavoriteChannel, ...]:
        return tuple(self._favorites)

    def load(self) -> tuple[FavoriteChannel, ...]:
        if not self.path.exists():
            self._favorites = []
            return ()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raw = []
        loaded: list[FavoriteChannel] = []
        for index, item in enumerate(raw if isinstance(raw, list) else []):
            if not isinstance(item, dict):
                continue
            try:
                loaded.append(FavoriteChannel(
                    target=item["target"],
                    timeslot=item.get("timeslot", 2),
                    call_type=item.get("call_type", "group"),
                    default_name=item.get("default_name", ""),
                    custom_name=item.get("custom_name", ""),
                    note=item.get("note", ""),
                    position=item.get("position", index),
                ).normalized())
            except (KeyError, TypeError, ValueError):
                continue
        loaded.sort(key=lambda fav: fav.position)
        self._favorites = [self._with_position(fav, i) for i, fav in enumerate(loaded)]
        return self.favorites

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = [self._as_dict(fav) for fav in self._favorites]
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def add(self, favorite: FavoriteChannel) -> FavoriteChannel:
        normalized = self._with_position(favorite.normalized(), len(self._favorites))
        existing = self.find(normalized.target, normalized.timeslot, normalized.call_type)
        if existing is not None:
            raise ValueError("Dieser DMR-Kanal ist bereits als Favorit gespeichert.")
        self._favorites.append(normalized)
        self.save()
        return normalized

    def update(self, old: FavoriteChannel, new: FavoriteChannel) -> FavoriteChannel:
        index = self._favorites.index(old)
        normalized = self._with_position(new.normalized(), index)
        duplicate = self.find(normalized.target, normalized.timeslot, normalized.call_type)
        if duplicate is not None and duplicate != old:
            raise ValueError("Dieser DMR-Kanal ist bereits als Favorit gespeichert.")
        self._favorites[index] = normalized
        self.save()
        return normalized

    def remove(self, favorite: FavoriteChannel) -> None:
        self._favorites.remove(favorite)
        self._renumber_and_save()

    def move(self, old_index: int, new_index: int) -> None:
        if old_index == new_index or not (0 <= old_index < len(self._favorites)):
            return
        new_index = max(0, min(new_index, len(self._favorites) - 1))
        item = self._favorites.pop(old_index)
        self._favorites.insert(new_index, item)
        self._renumber_and_save()

    def replace_order(self, favorites: list[FavoriteChannel]) -> None:
        self._favorites = [self._with_position(fav.normalized(), i) for i, fav in enumerate(favorites)]
        self.save()

    def find(self, target: int, timeslot: int, call_type: str) -> FavoriteChannel | None:
        call_type = str(call_type).lower()
        return next((fav for fav in self._favorites if fav.target == int(target) and fav.timeslot == int(timeslot) and fav.call_type == call_type), None)

    def export_json(self, path: Path) -> None:
        Path(path).write_text(json.dumps([self._as_dict(f) for f in self._favorites], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def export_csv(self, path: Path) -> None:
        with Path(path).open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["custom_name", "default_name", "target", "timeslot", "call_type", "note", "position"])
            writer.writeheader()
            writer.writerows(self._as_dict(f) for f in self._favorites)

    def import_json(self, path: Path) -> int:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("Die Favoritendatei muss eine JSON-Liste enthalten.")
        return self._import_rows(raw)

    def import_csv(self, path: Path) -> int:
        with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
            return self._import_rows(list(csv.DictReader(handle)))

    def _import_rows(self, rows) -> int:
        added = 0
        for item in rows:
            try:
                fav = FavoriteChannel(
                    target=item["target"], timeslot=item.get("timeslot", 2), call_type=item.get("call_type", "group"),
                    default_name=item.get("default_name", item.get("name", "")), custom_name=item.get("custom_name", ""),
                    note=item.get("note", ""), position=len(self._favorites),
                ).normalized()
            except (KeyError, TypeError, ValueError):
                continue
            if self.find(fav.target, fav.timeslot, fav.call_type) is None:
                self._favorites.append(self._with_position(fav, len(self._favorites)))
                added += 1
        self.save()
        return added

    def _renumber_and_save(self) -> None:
        self._favorites = [self._with_position(fav, i) for i, fav in enumerate(self._favorites)]
        self.save()

    @staticmethod
    def _with_position(fav: FavoriteChannel, position: int) -> FavoriteChannel:
        return FavoriteChannel(fav.target, fav.timeslot, fav.call_type, fav.default_name, fav.custom_name, fav.note, position)

    @staticmethod
    def _as_dict(fav: FavoriteChannel) -> dict:
        return {
            "custom_name": fav.custom_name,
            "default_name": fav.default_name,
            "target": fav.target,
            "timeslot": fav.timeslot,
            "call_type": fav.call_type,
            "note": fav.note,
            "position": fav.position,
        }
