"""Lokale Präferenzen für den zuletzt verwendeten Funkbetrieb."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class OperatingPreferences:
    talkgroup: int = 91
    timeslot: int = 2
    call_type: str = "group"
    speech_enabled: bool = False

    def normalized(self) -> "OperatingPreferences":
        tg = self.talkgroup if isinstance(self.talkgroup, int) and self.talkgroup > 0 else 91
        ts = self.timeslot if self.timeslot in {1, 2} else 2
        call_type = self.call_type if self.call_type in {"group", "private"} else "group"
        return OperatingPreferences(tg, ts, call_type, bool(self.speech_enabled))


class OperatingPreferencesStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def load(self) -> OperatingPreferences:
        if not self.path.exists():
            return OperatingPreferences()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return OperatingPreferences()
        return OperatingPreferences(
            talkgroup=int(data.get("talkgroup", 91)),
            timeslot=int(data.get("timeslot", 2)),
            call_type=str(data.get("call_type", "group")).strip().lower(),
            speech_enabled=bool(data.get("speech_enabled", False)),
        ).normalized()

    def save(self, preferences: OperatingPreferences) -> None:
        value = preferences.normalized()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "talkgroup": value.talkgroup,
            "timeslot": value.timeslot,
            "call_type": value.call_type,
            "speech_enabled": value.speech_enabled,
        }
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(self.path)
