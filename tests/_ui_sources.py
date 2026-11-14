"""Hilfen für Quelltext-Tests der Qt-Oberfläche.

Seit 0.2.1.87 ist das Hauptfenster auf mehrere Module verteilt
(``main_window.py`` plus ``main_window_*.py``). Quelltext-Tests lesen es
deshalb über ``main_window_source()`` als Ganzes.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI_QT = ROOT / "carendmr" / "ui_qt"
MAIN_WINDOW_PARTS = (
    "main_window.py",
    "main_window_logbook.py",
    "main_window_windows.py",
    "main_window_audio.py",
    "main_window_channels.py",
    "main_window_radio.py",
)


def main_window_source() -> str:
    """Gesamter Quelltext des Hauptfensters in fester Reihenfolge."""
    parts = []
    for index, name in enumerate(MAIN_WINDOW_PARTS):
        text = (UI_QT / name).read_text(encoding="utf-8")
        if index:
            text = text.replace("from __future__ import annotations\n", "")
        parts.append(text)
    return "\n".join(parts)
