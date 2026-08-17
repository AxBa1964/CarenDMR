"""Unabhängiger BrandMeister-Last-Heard-Client für den TG-Monitor."""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

BRANDMEISTER_LASTHEARD_URL = "https://api.brandmeister.network"
BRANDMEISTER_LASTHEARD_SOCKET_PATH = "/lh/socket.io"


@dataclass(frozen=True, slots=True)
class TalkgroupActivity:
    target: int
    source_id: int
    callsign: str
    source_name: str
    talkgroup_name: str
    started_at: int
    stopped_at: int
    session_id: str
    active: bool

    @property
    def duration_seconds(self) -> int:
        end = int(time.time()) if self.active else self.stopped_at
        return max(0, end - self.started_at)


class TalkgroupActivityService:
    """Socket.IO läuft ausschließlich in einem eigenen Monitor-Thread."""

    def __init__(
        self,
        monitored_talkgroups: set[int],
        *,
        on_activity: Callable[[TalkgroupActivity], None],
        on_status: Callable[[str], None] | None = None,
        log_path: Path | None = None,
    ) -> None:
        self._monitored = {int(tg) for tg in monitored_talkgroups if int(tg) > 0}
        self._on_activity = on_activity
        self._on_status = on_status or (lambda _message: None)
        self._thread: threading.Thread | None = None
        self._client = None
        self._stop = threading.Event()
        self._log_path = Path(log_path) if log_path is not None else None
        self._log_lock = threading.Lock()


    def _log(self, message: str) -> None:
        """Schreibt Diagnoseinformationen fehlertolerant in eine eigene Logdatei."""
        if self._log_path is None:
            return
        try:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().astimezone().isoformat(timespec="milliseconds")
            line = f"{stamp} {message}\n"
            with self._log_lock:
                with self._log_path.open("a", encoding="utf-8") as handle:
                    handle.write(line)
        except OSError:
            # Diagnose darf den Monitor niemals beeinflussen.
            pass

    @property
    def monitored_talkgroups(self) -> set[int]:
        return set(self._monitored)

    def set_monitored_talkgroups(self, values: set[int]) -> None:
        self._monitored = {int(tg) for tg in values if int(tg) > 0}
        self._log(f"FILTER TGs={sorted(self._monitored)}")

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="CarenDMR-TG-Monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        client = self._client
        if client is not None:
            try:
                client.disconnect()
            except Exception:
                pass

    def _run(self) -> None:
        self._log(
            f"START URL={BRANDMEISTER_LASTHEARD_URL} "
            f"PATH={BRANDMEISTER_LASTHEARD_SOCKET_PATH} TGs={sorted(self._monitored)}"
        )
        try:
            import socketio
        except ImportError:
            self._log("FEHLER python-socketio fehlt")
            self._on_status("Fehlt: python-socketio[client]. Bitte requirements.txt installieren.")
            return

        client = socketio.Client(reconnection=True, logger=False, engineio_logger=False)
        self._client = client

        @client.event
        def connect():
            self._log("VERBUNDEN Socket.IO")
            client.emit("join", "everything")
            self._log("SUBSCRIBE join=everything")
            self._on_status("Mit BrandMeister Last Heard verbunden.")

        @client.event
        def disconnect(reason=None):
            self._log(f"GETRENNT reason={reason!r} stop={self._stop.is_set()}")
            if not self._stop.is_set():
                self._on_status("BrandMeister Last Heard getrennt – Wiederverbindung läuft …")

        @client.on("mqtt")
        def on_mqtt(data):
            try:
                raw = json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str)
            except Exception:
                raw = repr(data)
            self._log(f"MQTT RAW={raw}")

            activity = self._parse_activity(data)
            if activity is None:
                self._log("PARSE VERWORFEN: kein auswertbarer DMR-Call")
                return

            monitored = activity.target in self._monitored
            self._log(
                "PARSE "
                f"TG={activity.target} Src={activity.source_id} Call={activity.callsign or '-'} "
                f"Name={activity.source_name or '-'} TGName={activity.talkgroup_name or '-'} "
                f"Start={activity.started_at} Stop={activity.stopped_at} "
                f"Session={activity.session_id or '-'} Aktiv={activity.active} "
                f"FILTER={'TREFFER' if monitored else 'IGNORIERT'}"
            )
            if monitored:
                self._on_activity(activity)

        try:
            self._log("VERBINDUNG wird aufgebaut")
            self._on_status("Verbinde mit BrandMeister Last Heard …")
            client.connect(
                BRANDMEISTER_LASTHEARD_URL,
                socketio_path=BRANDMEISTER_LASTHEARD_SOCKET_PATH,
                transports=["websocket"],
                wait_timeout=10,
            )
            client.wait()
        except Exception as error:
            self._log(f"FEHLER {type(error).__name__}: {error}")
            if not self._stop.is_set():
                self._on_status(f"BrandMeister Last Heard nicht verfügbar: {error}")
        finally:
            self._log("ENDE Monitor-Thread")
            self._client = None

    @staticmethod
    def _parse_activity(data) -> TalkgroupActivity | None:
        try:
            payload = data.get("payload") if isinstance(data, dict) else None
            call = json.loads(payload) if isinstance(payload, str) else payload
            if not isinstance(call, dict):
                return None
            target = int(call.get("DestinationID", 0))
            if target <= 0:
                return None
            start = int(call.get("Start", 0) or 0)
            stop = int(call.get("Stop", 0) or 0)
            event = str(call.get("Event", ""))
            active = stop <= 0 and event != "Session-Stop"
            return TalkgroupActivity(
                target=target,
                source_id=int(call.get("SourceID", 0) or 0),
                callsign=str(call.get("SourceCall", "") or "").strip().upper(),
                source_name=str(call.get("SourceName", "") or "").strip(),
                talkgroup_name=str(call.get("DestinationName", "") or "").strip(),
                started_at=start,
                stopped_at=stop,
                session_id=str(call.get("SessionID", "") or ""),
                active=active,
            )
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
