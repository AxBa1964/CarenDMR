"""Speichern und Laden der lokalen Audioauswahl."""

from __future__ import annotations

import json
from pathlib import Path

from .devices import AudioDirection, AudioSelection


class AudioConfigStore:
    """Speichert ausschließlich lokale Audio-Gerätepräferenzen."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> dict[AudioDirection, AudioSelection]:
        if not self.path.exists():
            return {}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(
                f"Die Audio-Konfiguration '{self.path}' ist nicht lesbar."
            ) from exc

        result: dict[AudioDirection, AudioSelection] = {}
        for key in ("input", "output"):
            value = raw.get(key)
            if value is None:
                continue
            selection = AudioSelection.from_dict(value)
            expected = AudioDirection(key)
            if selection.direction is not expected:
                raise ValueError(
                    f"Ungültige Richtung für Audioauswahl '{key}'."
                )
            result[expected] = selection
        return result

    def save(
        self,
        selections: dict[AudioDirection, AudioSelection],
    ) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            direction.value: selection.to_dict()
            for direction, selection in selections.items()
        }
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)
