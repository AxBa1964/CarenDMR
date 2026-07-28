from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ConfigError(RuntimeError):
    pass


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"Konfigurationsdatei fehlt: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"Konfigurationsdatei ist ungültig: Zeile {exc.lineno}, Spalte {exc.colno}"
        ) from exc

    _validate_config(data)
    return data


def _validate_config(data: dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise ConfigError("Die Konfiguration muss ein JSON-Objekt sein.")

    dmr = data.get("dmr")
    if not isinstance(dmr, dict):
        raise ConfigError("Abschnitt 'dmr' fehlt.")

    default_tg = dmr.get("default_talkgroup")
    if not isinstance(default_tg, int) or default_tg <= 0:
        raise ConfigError("'dmr.default_talkgroup' muss eine positive Zahl sein.")

    logging_cfg = data.get("logging")
    if not isinstance(logging_cfg, dict):
        raise ConfigError("Abschnitt 'logging' fehlt.")

    directory = logging_cfg.get("directory")
    if not isinstance(directory, str) or not directory.strip():
        raise ConfigError("'logging.directory' darf nicht leer sein.")
