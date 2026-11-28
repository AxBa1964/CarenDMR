"""Lautstärke und Mikrofonpegel der Box (schreibt ``config/audio_send.local.json``).

Nur die beiden Zahlen – ohne den vollen AudioSendService und ohne sounddevice,
damit die Web-App sie auch ohne laufenden Funk ändern kann. Dieselbe Datei liest
der Funkkern beim Start.
"""
from __future__ import annotations

import json
from pathlib import Path

MAX_PERCENT = 400
SETTINGS_FILE = "audio_send.local.json"


class BoxAudioSettingsError(ValueError):
    """Ungültiger Wert für Lautstärke oder Mikrofonpegel."""


class BoxAudioSettings:
    def __init__(self, project_root: Path) -> None:
        self._path = Path(project_root) / "config" / SETTINGS_FILE

    def _load(self) -> dict:
        if not self._path.is_file():
            return {}
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def output_volume_percent(self) -> int:
        return self._clamp(self._load().get("output_volume_percent", 100))

    def microphone_gain_percent(self) -> int:
        return self._clamp(self._load().get("microphone_gain_percent", 100))

    def save(self, *, output_volume_percent: int, microphone_gain_percent: int) -> None:
        data = self._load()
        data["output_volume_percent"] = self._require(output_volume_percent, "Die Lautstärke")
        data["microphone_gain_percent"] = self._require(microphone_gain_percent, "Der Mikrofonpegel")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(self._path)

    @staticmethod
    def _clamp(value: object) -> int:
        try:
            return max(0, min(MAX_PERCENT, int(round(float(value)))))
        except (TypeError, ValueError):
            return 100

    @staticmethod
    def _require(value: object, label: str) -> int:
        try:
            number = int(round(float(value)))
        except (TypeError, ValueError) as error:
            raise BoxAudioSettingsError(f"{label} muss eine Zahl sein.") from error
        if not 0 <= number <= MAX_PERCENT:
            raise BoxAudioSettingsError(f"{label} muss zwischen 0 und {MAX_PERCENT} Prozent liegen.")
        return number
