"""Programm- und Datenpfade für Quellcode-Start und Windows-Exe.

CarenDMR unterscheidet ab 0.2.1.88 zwei Orte:

* **Programmordner** – mitgelieferte, unveränderliche Dateien
  (``native/``, ``config/config.json``, ``config/talkgroups.json``,
  Beispielkonfigurationen).
* **Datenordner** – alles, was der Nutzer ändert oder was CarenDMR schreibt
  (``config/*.local.json``, ``logs/``, ``data/``, ``Mitschnitte/``,
  ``firmware/``).

Beim Start aus dem Quellcode sind beide Orte das Projektverzeichnis; das
bisherige Verhalten bleibt damit unverändert. In der Exe (PyInstaller) liegt
der Programmordner neben bzw. in der Exe, der Datenordner unter
``%LOCALAPPDATA%\\CarenDMR``. Mit der Umgebungsvariable ``CARENDMR_DATA_DIR``
lässt sich der Datenordner in beiden Fällen überschreiben.

Alle Dienste erhalten weiterhin ``project_root``; das ist ab jetzt der
Datenordner. Nur Programmdateien werden über :func:`program_root` bzw.
:func:`native_dir` gesucht.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

APP_NAME = "CarenDMR"
DATA_DIR_ENV = "CARENDMR_DATA_DIR"

# Dateien aus config/, die beim ersten Start in den Datenordner kopiert werden,
# falls sie dort fehlen. Bestehende Dateien werden nie überschrieben.
_SEED_CONFIG_FILES = ("config.json", "talkgroups.json")


def is_frozen() -> bool:
    """True, wenn CarenDMR als gebündelte Exe (PyInstaller) läuft."""
    return bool(getattr(sys, "frozen", False))


def source_root() -> Path:
    """Projektverzeichnis beim Start aus dem Quellcode."""
    return Path(__file__).resolve().parent.parent


def program_root() -> Path:
    """Ordner mit den mitgelieferten Programmdateien."""
    if is_frozen():
        bundle = getattr(sys, "_MEIPASS", None)
        if bundle:
            return Path(bundle)
        return Path(sys.executable).resolve().parent
    return source_root()


def default_data_root() -> Path:
    override = os.environ.get(DATA_DIR_ENV, "").strip()
    if override:
        return Path(override).expanduser()
    if not is_frozen():
        return source_root()
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA", "").strip()
        if base:
            return Path(base) / APP_NAME
        return Path.home() / "AppData" / "Local" / APP_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    xdg = os.environ.get("XDG_DATA_HOME", "").strip()
    return (Path(xdg) if xdg else Path.home() / ".local" / "share") / APP_NAME


def native_dir(project_root: Path | None = None) -> Path:
    """Ordner mit den nativen Bibliotheken (DLL/so/dylib).

    In der Exe immer im Programmordner. Beim Quellcode-Start im übergebenen
    Projektverzeichnis, damit Tests und Werkzeuge mit eigenen Wurzeln arbeiten
    können.
    """
    if is_frozen():
        return program_root() / "native"
    if project_root is None:
        return source_root() / "native"
    root = project_root if isinstance(project_root, Path) else Path(project_root)
    override = os.environ.get(DATA_DIR_ENV, "").strip()
    if override:
        try:
            if root.resolve() == Path(override).expanduser().resolve():
                # Datenordner per Umgebungsvariable umgelenkt: die nativen
                # Bibliotheken bleiben im Projektverzeichnis.
                return source_root() / "native"
        except OSError:
            pass
    return root / "native"


def firmware_dir(project_root: Path) -> Path:
    """Ablage der vom Nutzer bereitgestellten Codec-Dateien."""
    return Path(project_root) / "firmware"


def prepare_data_root(data_root: Path, program: Path | None = None) -> list[Path]:
    """Legt den Datenordner an und kopiert fehlende Startdateien hinein.

    Gibt die neu kopierten Dateien zurück. Liegt der Datenordner im
    Programmordner (Quellcode-Start), wird nichts kopiert.
    """
    data_root = Path(data_root)
    program = Path(program) if program is not None else program_root()
    for name in ("config", "logs", "data"):
        (data_root / name).mkdir(parents=True, exist_ok=True)

    copied: list[Path] = []
    try:
        same_place = data_root.resolve() == program.resolve()
    except OSError:
        same_place = False
    if same_place:
        return copied

    source_config = program / "config"
    if not source_config.is_dir():
        return copied
    candidates = [source_config / name for name in _SEED_CONFIG_FILES]
    candidates.extend(sorted(source_config.glob("*.example.json")))
    for source in candidates:
        if not source.is_file():
            continue
        target = data_root / "config" / source.name
        if target.exists():
            continue
        shutil.copy2(source, target)
        copied.append(target)
    return copied


def tg_monitor_command(project_root: Path) -> list[str] | None:
    """Befehl zum Start des eigenständigen TG-Monitors.

    In der Exe startet sich das Programm selbst mit ``--tg-monitor``;
    beim Quellcode-Start wird wie bisher ``tg_monitor.py`` ausgeführt.
    Liefert ``None``, wenn das Skript fehlt.
    """
    if is_frozen():
        return [sys.executable, "--tg-monitor"]
    script = source_root() / "tg_monitor.py"
    if not script.is_file():
        script = Path(project_root) / "tg_monitor.py"
    if not script.is_file():
        return None
    return [sys.executable, str(script)]
