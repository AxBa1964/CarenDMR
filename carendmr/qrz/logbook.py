"""QRZ.com Logbook API integration for explicitly confirmed QSOs."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode
from urllib.request import Request, urlopen

from carendmr.version import __version__

QRZ_LOGBOOK_URL = "https://logbook.qrz.com/api"


class QrzLogbookError(RuntimeError):
    pass


@dataclass(frozen=True)
class QrzLogbookConfig:
    enabled: bool = False
    api_key: str = ""

    @classmethod
    def load(cls, path: Path) -> "QrzLogbookConfig":
        path = Path(path)
        if not path.exists():
            return cls()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise QrzLogbookError("QRZ-Logbook-Konfiguration ist nicht lesbar.") from error
        return cls(bool(raw.get("enabled", False)), str(raw.get("api_key", "")).strip())

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"enabled": self.enabled, "api_key": self.api_key}, indent=2) + "\n", encoding="utf-8")


@dataclass(frozen=True)
class QrzLogResult:
    logid: str
    result: str = "OK"


def _adif_field(name: str, value: str) -> str:
    value = str(value)
    return f"<{name}:{len(value)}>{value}"


def build_dmr_adif(*, callsign: str, station_callsign: str, qso_at: datetime,
                   talkgroup: int, timeslot: int, band: str = "70cm") -> str:
    call = callsign.strip().upper()
    own = station_callsign.strip().upper()
    if not call or not own:
        raise QrzLogbookError("Für QRZ müssen beide Rufzeichen bekannt sein.")
    if qso_at.tzinfo is None:
        qso_at = qso_at.replace(tzinfo=timezone.utc)
    utc = qso_at.astimezone(timezone.utc)
    comment = f"CarenDMR BrandMeister TG {int(talkgroup)} TS{int(timeslot)}"
    fields = (
        ("call", call), ("station_callsign", own),
        ("qso_date", utc.strftime("%Y%m%d")), ("time_on", utc.strftime("%H%M")),
        ("band", band), ("mode", "DMR"), ("comment", comment),
    )
    return "".join(_adif_field(k, v) for k, v in fields) + "<eor>"


class QrzLogbookService:
    def __init__(self, config_path: Path) -> None:
        self.config_path = Path(config_path)

    @property
    def config(self) -> QrzLogbookConfig:
        return QrzLogbookConfig.load(self.config_path)

    @property
    def configured(self) -> bool:
        cfg = self.config
        return cfg.enabled and bool(cfg.api_key)

    def insert_dmr_qso(self, *, callsign: str, station_callsign: str, qso_at: datetime,
                       talkgroup: int, timeslot: int) -> QrzLogResult:
        cfg = self.config
        if not cfg.enabled:
            raise QrzLogbookError("QRZ.com Logbook ist in den Einstellungen nicht aktiviert.")
        if not cfg.api_key:
            raise QrzLogbookError("QRZ.com API Access Key fehlt.")
        adif = build_dmr_adif(callsign=callsign, station_callsign=station_callsign,
                              qso_at=qso_at, talkgroup=talkgroup, timeslot=timeslot)
        body = urlencode({"KEY": cfg.api_key, "ACTION": "INSERT", "ADIF": adif}).encode("utf-8")
        request = Request(QRZ_LOGBOOK_URL, data=body, method="POST", headers={
            "User-Agent": f"CarenDMR/{__version__}",
            "Content-Type": "application/x-www-form-urlencoded",
        })
        try:
            with urlopen(request, timeout=15.0) as response:
                text = response.read().decode("utf-8", errors="replace")
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            raise QrzLogbookError(f"QRZ.com Logbook ist nicht erreichbar: {error}") from error
        values = {k.upper(): v[-1] for k, v in parse_qs(text, keep_blank_values=True).items()}
        result = values.get("RESULT", "").upper()
        if result not in {"OK", "REPLACE"}:
            reason = values.get("REASON", "Unbekannte QRZ-Antwort")
            if result == "AUTH":
                reason = "API Access Key hat keine Berechtigung für INSERT."
            raise QrzLogbookError(f"QRZ.com: {reason}")
        logid = values.get("LOGID") or values.get("LOGIDS") or ""
        if not logid:
            raise QrzLogbookError("QRZ.com meldete Erfolg, aber keine LOGID.")
        return QrzLogResult(logid=logid, result=result)
