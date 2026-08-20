"""ADIF-QSO-Weitergabe per WSJT-X-kompatiblem UDP Logged-ADIF-Paket."""
from __future__ import annotations

import json
import socket
import struct
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from carendmr.version import __version__

_MAGIC = 0xADBCCBDA
_SCHEMA = 3
_LOGGED_ADIF = 12


class AdifUdpError(RuntimeError):
    pass


@dataclass(frozen=True)
class AdifUdpConfig:
    enabled: bool = False
    host: str = "127.0.0.1"
    port: int = 2237

    @classmethod
    def load(cls, path: Path) -> "AdifUdpConfig":
        path = Path(path)
        if not path.exists():
            return cls()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise AdifUdpError("ADIF-UDP-Konfiguration ist nicht lesbar.") from error
        host = str(raw.get("host", "127.0.0.1")).strip() or "127.0.0.1"
        try:
            port = int(raw.get("port", 2237))
        except (TypeError, ValueError) as error:
            raise AdifUdpError("ADIF-UDP-Port ist ungültig.") from error
        if not 1 <= port <= 65535:
            raise AdifUdpError("ADIF-UDP-Port muss zwischen 1 und 65535 liegen.")
        return cls(bool(raw.get("enabled", False)), host, port)

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"enabled": self.enabled, "host": self.host, "port": self.port}, indent=2) + "\n",
            encoding="utf-8",
        )


def _field(name: str, value: str) -> str:
    text = str(value)
    return f"<{name.upper()}:{len(text.encode('utf-8'))}>{text}"


def build_adif(*, callsign: str, station_callsign: str, qso_at: datetime,
               talkgroup: int, timeslot: int, name: str = "", country: str = "") -> str:
    call = callsign.strip().upper()
    own = station_callsign.strip().upper()
    if not call or not own:
        raise AdifUdpError("Für ADIF-UDP müssen beide Rufzeichen bekannt sein.")
    if qso_at.tzinfo is None:
        qso_at = qso_at.replace(tzinfo=timezone.utc)
    utc = qso_at.astimezone(timezone.utc)
    fields = [
        ("CALL", call),
        ("STATION_CALLSIGN", own),
        ("QSO_DATE", utc.strftime("%Y%m%d")),
        ("TIME_ON", utc.strftime("%H%M%S")),
        ("BAND", "70CM"),
        ("MODE", "DIGITALVOICE"),
        ("SUBMODE", "DMR"),
        ("RST_SENT", "59"),
        ("RST_RCVD", "59"),
        ("COMMENT", f"CarenDMR BrandMeister TG {int(talkgroup)} TS{int(timeslot)}"),
    ]
    if name.strip():
        fields.append(("NAME", name.strip()))
    if country.strip():
        fields.append(("COUNTRY", country.strip()))
    record = "".join(_field(k, v) for k, v in fields) + "<EOR>"
    return (
        _field("ADIF_VER", "3.1.4")
        + _field("PROGRAMID", "CarenDMR")
        + _field("PROGRAMVERSION", __version__)
        + "<EOH>"
        + record
    )


def _qbytearray(value: str) -> bytes:
    data = value.encode("utf-8")
    return struct.pack(">I", len(data)) + data


def build_wsjt_logged_adif_packet(adif_text: str, *, app_id: str = "CarenDMR") -> bytes:
    return (
        struct.pack(">III", _MAGIC, _SCHEMA, _LOGGED_ADIF)
        + _qbytearray(app_id)
        + _qbytearray(adif_text)
    )


class AdifUdpService:
    def __init__(self, config_path: Path) -> None:
        self.config_path = Path(config_path)

    @property
    def config(self) -> AdifUdpConfig:
        return AdifUdpConfig.load(self.config_path)

    @property
    def configured(self) -> bool:
        return self.config.enabled

    def send_qso(self, *, callsign: str, station_callsign: str, qso_at: datetime,
                 talkgroup: int, timeslot: int, name: str = "", country: str = "") -> tuple[str, int, int]:
        cfg = self.config
        if not cfg.enabled:
            raise AdifUdpError("ADIF-UDP ist in den Einstellungen nicht aktiviert.")
        adif = build_adif(
            callsign=callsign, station_callsign=station_callsign, qso_at=qso_at,
            talkgroup=talkgroup, timeslot=timeslot, name=name, country=country,
        )
        packet = build_wsjt_logged_adif_packet(adif)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sent = sock.sendto(packet, (cfg.host, cfg.port))
        except OSError as error:
            raise AdifUdpError(f"ADIF-UDP konnte nicht gesendet werden: {error}") from error
        if sent != len(packet):
            raise AdifUdpError("ADIF-UDP-Datagramm wurde nicht vollständig gesendet.")
        return cfg.host, cfg.port, sent
