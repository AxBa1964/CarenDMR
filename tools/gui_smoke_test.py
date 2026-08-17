"""Startet die CarenDMR-GUI kurz und beendet sie wieder.

Der Test prüft ausschließlich, ob alle Widgets ohne Tcl/Tk-Fehler aufgebaut
werden. Es wird keine BrandMeister-Verbindung hergestellt.
"""
from __future__ import annotations

from pathlib import Path

from carendmr.ui.main_window import MainWindow


def main() -> int:
    project_root = Path(__file__).resolve().parent.parent
    window = MainWindow(project_root)
    window.root.update_idletasks()
    window.root.update()
    width = window.root.winfo_width()
    height = window.root.winfo_height()
    window.root.destroy()
    print(f"GUI-Smoke-Test erfolgreich: {width} x {height}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
