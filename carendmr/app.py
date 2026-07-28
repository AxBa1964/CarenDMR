from __future__ import annotations

import platform
import sys
from pathlib import Path

from carendmr.config import ConfigError, load_config
from carendmr.logging_setup import configure_logging
from carendmr.version import __version__


def run() -> int:
    project_root = Path(__file__).resolve().parent.parent

    try:
        config = load_config(project_root / "config" / "config.json")
    except ConfigError as exc:
        print(f"CarenDMR konnte nicht gestartet werden: {exc}", file=sys.stderr)
        return 2

    logger = configure_logging(project_root / config["logging"]["directory"])

    logger.info("CarenDMR startet")
    logger.info("Version: %s", __version__)
    logger.info("Betriebssystem: %s %s", platform.system(), platform.release())
    logger.info("Python: %s", platform.python_version())
    logger.info("Standard-Talkgroup: %s", config["dmr"]["default_talkgroup"])

    print("CarenDMR")
    print("-" * 40)
    print(f"Version             : {__version__}")
    print(f"Betriebssystem      : {platform.system()} {platform.release()}")
    print(f"Python              : {platform.python_version()}")
    print(f"Standard-Talkgroup  : {config['dmr']['default_talkgroup']}")
    print("Status              : Grundsystem bereit")
    print()
    print("Hinweis: Diese Version verbindet sich noch nicht mit BrandMeister.")

    logger.info("CarenDMR Grundsystem ist bereit")
    return 0
