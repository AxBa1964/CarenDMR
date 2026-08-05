"""Plattformneutrale Bedienfunktionen und konfigurierbare Desktop-Hotkeys."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


DEFAULT_HOTKEYS: dict[str, str] = {
    "HELP": "F1",
    "TG_CHANGE": "F2",
    "STATUS": "F3",
    "REPEAT": "F4",
    "CONNECT": "F5",
    "TS_CHANGE": "F6",
    "CALLTYPE_CHANGE": "F7",
    "OPEN_OPERATION": "F8",
    "OPEN_HISTORY": "F9",
    "OPEN_SETTINGS": "F10",
    "CONFIRM_QSO": "F11",
    "PTT": "Space",
}

REQUIRED_HOTKEYS: frozenset[str] = frozenset({"CONNECT", "TS_CHANGE", "CALLTYPE_CHANGE", "PTT"})

FUNCTION_LABELS: dict[str, str] = {
    "HELP": "Kontext-Hilfe",
    "TG_CHANGE": "Talkgroup wechseln",
    "STATUS": "Betriebszustand ansagen",
    "REPEAT": "Letzte Meldung wiederholen",
    "CONNECT": "Verbinden oder trennen",
    "TS_CHANGE": "Timeslot wechseln",
    "CALLTYPE_CHANGE": "Rufart wechseln",
    "OPEN_OPERATION": "Betrieb öffnen",
    "OPEN_HISTORY": "QSO-Historie öffnen",
    "OPEN_SETTINGS": "Einstellungen öffnen",
    "CONFIRM_QSO": "QSO bestätigen",
    "PTT": "Senden (PTT)",
}


@dataclass(frozen=True)
class HotkeyConflict:
    key: str
    functions: tuple[str, ...]


class HotkeyManager:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._mapping = dict(DEFAULT_HOTKEYS)
        self.load()

    @property
    def mapping(self) -> dict[str, str]:
        return dict(self._mapping)

    def load(self) -> dict[str, str]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            return self.mapping
        if isinstance(raw, dict):
            for function, key in raw.items():
                if function in DEFAULT_HOTKEYS and isinstance(key, str):
                    normalized = self.normalize_key(key)
                    if function in REQUIRED_HOTKEYS and not normalized:
                        normalized = DEFAULT_HOTKEYS[function]
                    self._mapping[function] = normalized
        return self.mapping

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._mapping, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def reset(self) -> None:
        self._mapping = dict(DEFAULT_HOTKEYS)
        self.save()

    def set(self, function: str, key: str) -> None:
        if function not in DEFAULT_HOTKEYS:
            raise KeyError(function)
        normalized = self.normalize_key(key)
        if function in REQUIRED_HOTKEYS and not normalized:
            raise ValueError(f"{FUNCTION_LABELS[function]} benötigt zwingend einen Hotkey.")
        for other_function, other_key in self._mapping.items():
            if normalized and other_function != function and other_key.lower() == normalized.lower():
                raise ValueError(f"{normalized} ist bereits für {FUNCTION_LABELS.get(other_function, other_function)} belegt.")
        self._mapping[function] = normalized
        self.save()

    def conflicts(self) -> list[HotkeyConflict]:
        reverse: dict[str, list[str]] = {}
        for function, key in self._mapping.items():
            if not key:
                continue
            reverse.setdefault(key.lower(), []).append(function)
        return [HotkeyConflict(key=self._mapping[functions[0]], functions=tuple(functions))
                for functions in reverse.values() if len(functions) > 1]

    @staticmethod
    def normalize_key(key: str) -> str:
        value = key.strip()
        aliases = {" ": "Space", "spacebar": "Space", "leer": "Space", "leertaste": "Space"}
        return aliases.get(value.lower(), value)

    @staticmethod
    def tkinter_sequence(key: str, *, release: bool = False) -> str:
        normalized = HotkeyManager.normalize_key(key)
        prefix = "KeyRelease" if release else "KeyPress"
        if normalized.lower() == "space":
            return f"<{prefix}-space>"
        if normalized.upper().startswith("F") and normalized[1:].isdigit():
            return f"<{normalized.upper()}>" if not release else f"<KeyRelease-{normalized.upper()}>"
        parts = normalized.replace("Ctrl", "Control").replace("+", "-")
        return f"<{parts}>"
