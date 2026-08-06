"""Entkoppelte Erstellung der Audio-Labor-Berichte.

Die aufwendige Matplotlib-/FFT-Auswertung darf niemals im zeitkritischen
TX-/RX-Pfad laufen. Deshalb wird sie ausschließlich in einem Daemon-Thread
nach Abschluss der Funkverbindung gestartet.
"""
from __future__ import annotations

from pathlib import Path
from threading import Lock, Thread
from typing import Mapping

from .audio_lab import build_session_report
from .tx_rx_timing import mark as timing_mark

_active_lock = Lock()
_active_sessions: set[Path] = set()


def schedule_session_report(session_dir: Path, *, extra: Mapping[str, object] | None = None) -> bool:
    """Plant einen Bericht im Hintergrund ein.

    Gibt ``False`` zurück, wenn für denselben Sitzungsordner bereits eine
    Analyse läuft. Der Thread ist absichtlich ein Daemon, damit ein
    Programmende nicht auf Matplotlib warten muss.
    """
    path = Path(session_dir).resolve()
    with _active_lock:
        if path in _active_sessions:
            return False
        _active_sessions.add(path)

    payload = dict(extra or {})

    def worker() -> None:
        try:
            timing_mark("AUDIO_ANALYSE_START", f"Ordner={path}")
            build_session_report(path, extra=payload)
            timing_mark("AUDIO_ANALYSE_FERTIG", f"Ordner={path}")
        except Exception as exc:  # Diagnose darf den Funkbetrieb nie beenden.
            timing_mark("AUDIO_ANALYSE_FEHLER", f"{type(exc).__name__}: {exc}")
        finally:
            with _active_lock:
                _active_sessions.discard(path)

    Thread(target=worker, name="CarenDMR-Audioanalyse", daemon=True).start()
    return True
