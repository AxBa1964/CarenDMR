"""Lokale, deterministische Suche nach DMR-Kanälen."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from carendmr.domain import DmrChannel, FavoriteChannel
from carendmr.application.talkgroup_metadata import derive_talkgroup_metadata


class TalkgroupSearchService:
    """Lädt ein lokales Kanalverzeichnis und sortiert Treffer nach Relevanz."""

    def __init__(self, catalog_path: Path) -> None:
        self.catalog_path = Path(catalog_path)
        self._base_channels = self._load()
        self._favorites: tuple[FavoriteChannel, ...] = ()

    def reload(self) -> None:
        """Lädt den lokalen BrandMeister-Cache neu."""
        self._base_channels = self._load()

    def set_favorites(self, favorites) -> None:
        """Verknüpft persönliche Favoriten als Metadaten derselben Kanalliste."""
        self._favorites = tuple(favorites)

    @property
    def channels(self) -> tuple[DmrChannel, ...]:
        """Alle bekannten Kanäle inklusive privater, nur als Favorit vorhandener Ziele."""
        merged = list(self._base_channels)
        keys = {(c.target, c.timeslot, c.call_type) for c in merged}
        for favorite in self._favorites:
            key = (favorite.target, favorite.timeslot, favorite.call_type)
            channel = favorite.to_dmr_channel()
            if key in keys:
                enriched: list[DmrChannel] = []
                for existing in merged:
                    if (existing.target, existing.timeslot, existing.call_type) == key:
                        enriched.append(DmrChannel(
                            target=existing.target,
                            timeslot=favorite.timeslot,
                            call_type=favorite.call_type,
                            name=favorite.display_name,
                            country=existing.country,
                            description=existing.description,
                            language=existing.language,
                            language_source=existing.language_source,
                            language_confidence=existing.language_confidence,
                        ).normalized())
                    else:
                        enriched.append(existing)
                merged = enriched
            else:
                merged.append(channel)
                keys.add(key)
        return tuple(merged)

    def _load(self) -> tuple[DmrChannel, ...]:
        if not self.catalog_path.exists():
            return ()
        raw = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("Das Talkgroup-Verzeichnis muss eine JSON-Liste sein.")
        channels: list[DmrChannel] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            try:
                metadata = derive_talkgroup_metadata(item["target"], item.get("name", ""))
                channel = DmrChannel(
                    target=item["target"],
                    timeslot=item.get("timeslot", 2),
                    call_type=item.get("call_type", "group"),
                    name=item.get("name", ""),
                    country=item.get("country", "") or metadata.country_name,
                    description=item.get("description", ""),
                    language=item.get("language", "") or metadata.language,
                    language_source=item.get("language_source", "") or metadata.language_source,
                    language_confidence=item.get("language_confidence", 0.0) or metadata.language_confidence,
                ).normalized()
            except (KeyError, TypeError, ValueError):
                continue
            channels.append(channel)
        return tuple(channels)

    def search(self, query: str, *, limit: int = 10) -> list[DmrChannel]:
        text = str(query).strip().casefold()
        if not text or limit <= 0:
            return []

        scored: list[tuple[tuple[int, int, str, int], DmrChannel]] = []
        favorite_map = {(f.target, f.timeslot, f.call_type): f for f in self._favorites}
        for channel in self.channels:
            target = str(channel.target)
            name = channel.name.casefold()
            country = channel.country.casefold()
            description = channel.description.casefold()
            language = channel.language.casefold()

            rank: int | None = None
            if text == target:
                rank = 0
            elif target.startswith(text):
                rank = 1
            elif name.startswith(text):
                rank = 2
            elif text in name:
                rank = 3
            elif text in country or text in language or text in description:
                rank = 4
            if rank is None:
                continue
            favorite = favorite_map.get((channel.target, channel.timeslot, channel.call_type))
            favorite_rank = 0 if favorite is not None else 1
            favorite_position = favorite.position if favorite is not None else 999999
            # Favoriten zuerst, danach Relevanz und technische Sortierung.
            score = (favorite_rank, favorite_position, rank, len(target), name, channel.target)
            scored.append((score, channel))

        scored.sort(key=lambda item: item[0])
        return [channel for _, channel in scored[:limit]]


    def favorite_for(self, channel: DmrChannel) -> FavoriteChannel | None:
        key = (channel.target, channel.timeslot, channel.call_type)
        return next((f for f in self._favorites if (f.target, f.timeslot, f.call_type) == key), None)

    def display_name(self, channel: DmrChannel) -> str:
        favorite = self.favorite_for(channel)
        name = favorite.display_name if favorite is not None else (channel.name or str(channel.target))
        return f"★ {name}" if favorite is not None else name

    @staticmethod
    def format_target(channel: DmrChannel) -> str:
        """Formatiert nur die technische Zielspalte der Trefferliste."""
        target_prefix = "TG" if channel.is_group_call else "DMR-ID"
        return f"{target_prefix} {channel.target}"

    @classmethod
    def format_result(cls, channel: DmrChannel) -> str:
        """Kompatible einzeilige Textdarstellung für Logs und Accessibility."""
        name = channel.name or str(channel.target)
        return f"{name}, {cls.format_target(channel)}"
