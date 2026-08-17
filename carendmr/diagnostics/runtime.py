"""Laufzeitschalter für ausführliche Diagnoseausgaben."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

_lock = Lock()
_enabled = False
_config_path: Path | None = None


def initialize(project_root: Path) -> bool:
    """Lädt den gespeicherten Diagnoseschalter. Standard ist AUS."""
    global _enabled, _config_path
    _config_path = Path(project_root) / "config" / "diagnostics.local.json"
    enabled = False
    try:
        if _config_path.exists():
            data = json.loads(_config_path.read_text(encoding="utf-8"))
            enabled = bool(data.get("enabled", False))
    except (OSError, ValueError, TypeError):
        enabled = False
    with _lock:
        _enabled = enabled
    return enabled


def is_enabled() -> bool:
    with _lock:
        return _enabled


def set_enabled(enabled: bool, *, persist: bool = True) -> None:
    global _enabled
    with _lock:
        _enabled = bool(enabled)
    if persist and _config_path is not None:
        _config_path.parent.mkdir(parents=True, exist_ok=True)
        _config_path.write_text(
            json.dumps({"enabled": bool(enabled)}, indent=2) + "\n",
            encoding="utf-8",
        )


def diagnostic_print(*args: object, **kwargs: object) -> None:
    """Gibt nur bei aktivem Diagnosemodus auf der Konsole aus."""
    if is_enabled():
        print(*args, **kwargs)
