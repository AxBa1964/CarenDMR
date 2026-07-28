"""Konfiguration der Netzwerkgrundlage."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class NetworkConfig:
    """Verbindungsdaten für einen späteren BrandMeister-Master."""

    host: str
    port: int = 62031
    timeout_seconds: float = 3.0
    heartbeat_interval_seconds: float = 5.0

    def validate(self) -> None:
        if not self.host.strip():
            raise ValueError("Der Servername darf nicht leer sein.")
        if not 1 <= self.port <= 65535:
            raise ValueError("Der UDP-Port muss zwischen 1 und 65535 liegen.")
        if self.timeout_seconds <= 0:
            raise ValueError("Das Zeitlimit muss größer als null sein.")
        if self.heartbeat_interval_seconds <= 0:
            raise ValueError(
                "Das Heartbeat-Intervall muss größer als null sein."
            )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NetworkConfig":
        config = cls(
            host=str(data["host"]),
            port=int(data.get("port", 62031)),
            timeout_seconds=float(data.get("timeout_seconds", 3.0)),
            heartbeat_interval_seconds=float(
                data.get("heartbeat_interval_seconds", 5.0)
            ),
        )
        config.validate()
        return config


class NetworkConfigStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> NetworkConfig:
        if not self.path.exists():
            raise ValueError(
                f"Die Netzwerk-Konfiguration '{self.path}' fehlt. "
                "Bitte legen Sie sie anhand von "
                "'config/network.example.json' an."
            )
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(
                f"Die Netzwerk-Konfiguration '{self.path}' ist nicht lesbar."
            ) from exc
        if not isinstance(raw, dict):
            raise ValueError(
                "Die Netzwerk-Konfiguration muss ein JSON-Objekt sein."
            )
        try:
            return NetworkConfig.from_dict(raw)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"Die Netzwerk-Konfiguration ist ungültig: {exc}"
            ) from exc

    def save(self, config: NetworkConfig) -> None:
        config.validate()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(
                config.to_dict(),
                ensure_ascii=False,
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)
