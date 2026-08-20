"""Dateibasierte QSO-Synchronisation zwischen mehreren CarenDMR-Installationen.

Es wird bewusst keine aktive SQLite-Datei über OneDrive/Dropbox geteilt. Jede
Installation behält ihre lokale Datenbank und tauscht atomar JSON-Snapshots in
einem gemeinsamen Ordner aus.
"""
from __future__ import annotations

import json
import os
import socket
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class QsoSyncConfig:
    enabled: bool = False
    folder: str = ""

    @classmethod
    def load(cls, path: Path) -> "QsoSyncConfig":
        path = Path(path)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return cls()
        return cls(bool(data.get("enabled", False)), str(data.get("folder", "")).strip())

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"enabled": bool(self.enabled), "folder": self.folder.strip()}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class QsoSyncStore:
    """Verwaltet Gerätekennung und atomare Snapshot-Dateien."""

    SCHEMA = 1

    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root)
        self.config_path = self.project_root / "config" / "qso_sync.local.json"
        self.device_path = self.project_root / "config" / "qso_sync_device.local.json"

    @property
    def config(self) -> QsoSyncConfig:
        return QsoSyncConfig.load(self.config_path)

    def device_id(self) -> str:
        try:
            data = json.loads(self.device_path.read_text(encoding="utf-8"))
            value = str(data.get("device_id", "")).strip()
            if value:
                return value
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            pass
        self.device_path.parent.mkdir(parents=True, exist_ok=True)
        value = uuid.uuid4().hex
        payload = {
            "device_id": value,
            "device_name": socket.gethostname(),
            "created_at": _utc_now(),
        }
        self.device_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return value

    def folder(self) -> Path:
        cfg = self.config
        if not cfg.enabled:
            raise RuntimeError("QSO-Synchronisation ist nicht aktiviert.")
        if not cfg.folder:
            raise RuntimeError("Für die QSO-Synchronisation ist kein Ordner eingestellt.")
        folder = Path(os.path.expandvars(os.path.expanduser(cfg.folder)))
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def snapshot_path(self) -> Path:
        return self.folder() / f"CarenDMR_QSO_{self.device_id()}.json"

    def write_snapshot(self, payload: dict) -> Path:
        target = self.snapshot_path()
        payload = dict(payload)
        payload["schema"] = self.SCHEMA
        payload["device_id"] = self.device_id()
        payload["device_name"] = socket.gethostname()
        payload["generated_at"] = _utc_now()
        temp = target.with_suffix(target.suffix + f".{uuid.uuid4().hex}.tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temp, target)
        return target

    def peer_snapshots(self) -> list[dict]:
        folder = self.folder()
        own = self.snapshot_path().resolve()
        result: list[dict] = []
        for path in sorted(folder.glob("CarenDMR_QSO_*.json")):
            try:
                if path.resolve() == own:
                    continue
                data = json.loads(path.read_text(encoding="utf-8"))
                if int(data.get("schema", 0)) != self.SCHEMA:
                    continue
                result.append(data)
            except (OSError, ValueError, json.JSONDecodeError):
                continue
        return result
