"""Benutzeroberfläche; importiert Tk erst beim expliziten GUI-Start."""

from pathlib import Path


def run_gui(project_root: Path) -> int:
    from .main_window import run_gui as _run_gui
    return _run_gui(project_root)


__all__ = ["run_gui"]
