"""Lokale, deterministische Suche nach DMR-Kanälen."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from carendmr.domain import DmrChannel


class TalkgroupSearchService:
    """Lädt ein lokales Kanalverzeichnis und sortiert Treffer nach Relevanz."""

    def __init__(self, catalog_path: Path) -> None:
        self.catalog_path = Path(catalog_path)
        self._channels = self._load()

    @property
    def channels(self) -> tuple[DmrChannel, ...]:
        return self._channels

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
                channel = DmrChannel(
                    target=item["target"],
                    timeslot=item.get("timeslot", 2),
                    call_type=item.get("call_type", "group"),
                    name=item.get("name", ""),
                    country=item.get("country", ""),
                    description=item.get("description", ""),
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
        for channel in self._channels:
            target = str(channel.target)
            name = channel.name.casefold()
            country = channel.country.casefold()
            description = channel.description.casefold()

            rank: int | None = None
            if text == target:
                rank = 0
            elif target.startswith(text):
                rank = 1
            elif name.startswith(text):
                rank = 2
            elif text in name:
                rank = 3
            elif text in country or text in description:
                rank = 4
            if rank is None:
                continue
            # Innerhalb gleicher Relevanz: kürzere Nummern, dann Name und Ziel.
            score = (rank, len(target), name, channel.target)
            scored.append((score, channel))

        scored.sort(key=lambda item: item[0])
        return [channel for _, channel in scored[:limit]]

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
