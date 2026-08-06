"""BrandMeister-Talkgroup-Verzeichnis mit lokalem Offline-Cache."""
from __future__ import annotations

import json
from pathlib import Path
from urllib.request import Request, urlopen

from carendmr.application.talkgroup_metadata import derive_talkgroup_metadata


BRANDMEISTER_TALKGROUP_URL = "https://api.brandmeister.network/v2/talkgroup"


class TalkgroupCatalogService:
    def __init__(self, path: Path, *, url: str = BRANDMEISTER_TALKGROUP_URL) -> None:
        self.path = Path(path)
        self.url = url

    def update_from_brandmeister(self, *, timeout: float = 20.0) -> int:
        request = Request(
            self.url,
            headers={"User-Agent": "CarenDMR/0.1.7.4.3", "Accept": "application/json"},
        )
        with urlopen(request, timeout=timeout) as response:
            raw = json.loads(response.read().decode("utf-8-sig"))
        channels = self._normalize_api_payload(raw)
        self.save(channels)
        return len(channels)

    def save(self, channels: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(channels, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def _normalize_api_payload(raw) -> list[dict]:
        if not isinstance(raw, dict):
            raise ValueError("BrandMeister lieferte kein Talkgroup-Objekt.")
        channels: list[dict] = []
        for target, name in raw.items():
            try:
                number = int(str(target).strip())
            except ValueError:
                continue
            if number <= 0:
                continue
            clean_name = " ".join(str(name).replace("\r", " ").replace("\n", " ").split())
            metadata = derive_talkgroup_metadata(number, clean_name)
            channels.append({
                "target": number,
                "timeslot": 2,
                "call_type": "group",
                "name": clean_name,
                "country": metadata.country_name,
                "country_code": metadata.country_code,
                "description": "",
                "language": metadata.language,
                "language_source": metadata.language_source,
                "language_confidence": metadata.language_confidence,
            })
        channels.sort(key=lambda item: item["target"])
        return channels
