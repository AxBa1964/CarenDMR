"""Neustart und Herunterfahren der Box. Nur auf dem Raspberry Pi (Linux).

Auf anderen Systemen (z. B. dem Entwicklungs-PC) passiert absichtlich nichts,
damit niemand versehentlich seinen Rechner herunterfährt.
"""
from __future__ import annotations

import subprocess
import sys


class SystemControlError(RuntimeError):
    """Neustart/Herunterfahren nicht möglich (Klartext für die Oberfläche)."""


def _run(command: list[str], what: str) -> str:
    if not sys.platform.startswith("linux"):
        raise SystemControlError(
            f"{what} ist nur auf der Box (Raspberry Pi) möglich, nicht auf diesem Rechner."
        )
    try:
        subprocess.Popen(command)
    except (OSError, subprocess.SubprocessError) as error:
        raise SystemControlError(f"{what} fehlgeschlagen: {error}") from error
    return f"{what} wird ausgeführt."


def reboot() -> str:
    return _run(["sudo", "systemctl", "reboot"], "Neustart")


def shutdown() -> str:
    return _run(["sudo", "systemctl", "poweroff"], "Herunterfahren")
