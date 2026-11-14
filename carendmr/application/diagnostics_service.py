"""Diagnose-Schnittstelle für Oberflächen.

Bündelt den TX/RX-Timing-Log und den gespeicherten Diagnoseschalter, damit
Oberflächen nicht direkt auf ``carendmr.diagnostics`` zugreifen.
"""
from __future__ import annotations

from pathlib import Path

from carendmr.diagnostics import initialize as _initialize_switch
from carendmr.diagnostics import set_enabled as _set_switch
from carendmr.diagnostics.tx_rx_timing import initialize as _initialize_timing
from carendmr.diagnostics.tx_rx_timing import mark as _mark


def start_timing_log(project_root: Path) -> Path:
    """Öffnet den TX/RX-Timing-Log der Sitzung und liefert seinen Pfad."""
    return _initialize_timing(Path(project_root))


def timing_mark(step: str, detail: str = "") -> None:
    _mark(step, detail)


def load_diagnostics_enabled(project_root: Path) -> bool:
    """Lädt den gespeicherten Diagnoseschalter (Standard: aus)."""
    return bool(_initialize_switch(Path(project_root)))


def set_diagnostics_enabled(enabled: bool) -> None:
    _set_switch(bool(enabled))
