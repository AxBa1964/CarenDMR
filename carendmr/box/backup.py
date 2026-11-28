"""Sicherung der Box-Einstellungen – ohne Kennwörter und Keys.

Enthält Favoriten beider Netze, DMR-Station (ohne Hotspot-Passwort),
FM-Zugang (ohne Key) und die Audio-Lautstärken. Zum Übertragen auf eine
andere Box oder nach einer Neuinstallation.
"""
from __future__ import annotations

import json
from pathlib import Path

from carendmr.version import __version__


def build_backup(project_root: Path) -> dict:
    root = Path(project_root)
    backup: dict = {"carendmr_box_backup": 1, "version": __version__}

    from carendmr.box.favorites import BoxFavoritesService, NETWORKS

    favorites = BoxFavoritesService(root)
    backup["favorites"] = {
        network: {
            "favorites": [c.to_dict(network) for c in favorites.favorites(network)],
            "hotlist": [c.to_dict(network) if c else None for c in favorites.hotlist(network)],
        }
        for network in NETWORKS
    }

    from carendmr.box.audio_settings import BoxAudioSettings

    audio = BoxAudioSettings(root)
    backup["audio"] = {
        "output_volume_percent": audio.output_volume_percent(),
        "microphone_gain_percent": audio.microphone_gain_percent(),
    }

    station = _read_json(root / "config" / "brandmeister.local.json")
    if station:
        station.pop("password", None)
        backup["station"] = station

    fm = _read_json(root / "config" / "fm_funknetz.local.json")
    if fm:
        fm.pop("auth_key", None)
        backup["fm"] = fm

    return backup


def backup_json(project_root: Path) -> str:
    return json.dumps(build_backup(project_root), ensure_ascii=False, indent=2) + "\n"


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}
