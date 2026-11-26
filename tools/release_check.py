"""Kompakter Release-Check für CarenDMR."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "carendmr" / "version.py"
DOCUMENTS = ("README.md", "CHANGELOG.md", "RELEASE_INFO.md")
FORBIDDEN = (
    ROOT / "config" / "brandmeister.local.json",
    ROOT / "native" / "carendmr_mbe.dll",
    ROOT / "data" / "contacts.db",
    ROOT / "data" / "qso_history.db",
)


def version() -> str:
    match = re.search(r'__version__\s*=\s*"([^"]+)"', VERSION_FILE.read_text(encoding="utf-8"))
    if not match:
        raise RuntimeError("Versionsnummer fehlt in carendmr/version.py")
    return match.group(1)


def main() -> int:
    current = version()
    errors: list[str] = []
    for name in DOCUMENTS:
        text = (ROOT / name).read_text(encoding="utf-8")
        if current not in text:
            errors.append(f"{name} enthält Version {current} nicht")
    for path in FORBIDDEN:
        if path.exists() and path.is_file() and path.name != "carendmr_mbe.dll":
            # Lokale Dateien dürfen im Arbeitsverzeichnis existieren, aber niemals versioniert sein.
            pass
    if errors:
        print("Release-Check fehlgeschlagen:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"Release-Check OK: CarenDMR {current}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
