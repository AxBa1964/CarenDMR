"""Persistente Zeitmessung für den TX/RX-Umschaltpfad."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from threading import Lock
import json
from time import perf_counter

_lock = Lock()
_log_path: Path | None = None
_cycle_started = 0.0
_cycle_id = ""
_session_path: Path | None = None
_session_events: list[dict[str, object]] = []


def initialize(project_root: Path) -> Path:
    global _log_path
    _log_path = Path(project_root) / "logs" / "tx_rx_timing.log"
    _log_path.parent.mkdir(parents=True, exist_ok=True)
    return _log_path


def start_cycle(label: str) -> None:
    global _cycle_started, _cycle_id, _session_events
    with _lock:
        _cycle_started = perf_counter()
        _cycle_id = datetime.now().strftime("%Y%m%d-%H%M%S.%f")[:-3]
        _session_events = []
        _write_locked("START", label, 0.0)


def attach_session(session_dir: Path) -> Path:
    """Spiegelt die aktuelle TX/RX-Zeitachse in den Audio-Testordner."""
    global _session_path
    with _lock:
        _session_path = Path(session_dir) / "timeline.json"
        _session_path.parent.mkdir(parents=True, exist_ok=True)
        _flush_session_locked()
        return _session_path

def detach_session() -> None:
    global _session_path
    with _lock:
        _flush_session_locked()
        _session_path = None

def mark(step: str, detail: str = "") -> None:
    with _lock:
        elapsed_ms = (perf_counter() - _cycle_started) * 1000.0 if _cycle_started else 0.0
        _write_locked(step, detail, elapsed_ms)


def _flush_session_locked() -> None:
    if _session_path is None:
        return
    payload = {"cycle_id": _cycle_id, "events": _session_events}
    _session_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def _write_locked(step: str, detail: str, elapsed_ms: float) -> None:
    # Die Sitzungs-Timeline muss auch dann funktionieren, wenn das optionale
    # globale Textlog nicht initialisiert wurde. 0.1.8.3 verlor sonst alle
    # Ereignisse und schrieb eine leere timeline.json.
    timestamp = datetime.now().isoformat(timespec="milliseconds")
    safe_detail = str(detail).replace("\n", " ").replace("\t", " ")
    _session_events.append({"timestamp": timestamp, "elapsed_ms": round(elapsed_ms, 3), "step": step, "detail": safe_detail})
    _flush_session_locked()
    if _log_path is not None:
        with _log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{timestamp}\t{_cycle_id}\t{elapsed_ms:9.1f} ms\t{step}\t{safe_detail}\n")
