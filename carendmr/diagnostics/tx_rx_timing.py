"""Persistente Zeitmessung für den TX/RX-Umschaltpfad."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from threading import Lock
from time import perf_counter

_lock = Lock()
_log_path: Path | None = None
_cycle_started = 0.0
_cycle_id = ""


def initialize(project_root: Path) -> Path:
    global _log_path
    _log_path = Path(project_root) / "logs" / "tx_rx_timing.log"
    _log_path.parent.mkdir(parents=True, exist_ok=True)
    return _log_path


def start_cycle(label: str) -> None:
    global _cycle_started, _cycle_id
    with _lock:
        _cycle_started = perf_counter()
        _cycle_id = datetime.now().strftime("%Y%m%d-%H%M%S.%f")[:-3]
        _write_locked("START", label, 0.0)


def mark(step: str, detail: str = "") -> None:
    with _lock:
        elapsed_ms = (perf_counter() - _cycle_started) * 1000.0 if _cycle_started else 0.0
        _write_locked(step, detail, elapsed_ms)


def _write_locked(step: str, detail: str, elapsed_ms: float) -> None:
    if _log_path is None:
        return
    timestamp = datetime.now().isoformat(timespec="milliseconds")
    safe_detail = str(detail).replace("\n", " ").replace("\t", " ")
    with _log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{timestamp}\t{_cycle_id}\t{elapsed_ms:9.1f} ms\t{step}\t{safe_detail}\n")
