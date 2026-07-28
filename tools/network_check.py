"""Lokale Netzwerkprüfung für CarenDMR 0.0.6."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from carendmr.diagnostics import DiagnosticStatus, NetworkDiagnostics
from carendmr.network import NetworkConfigStore


CONFIG_PATH = PROJECT_ROOT / "config" / "network.local.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Prüft Netzwerk-Konfiguration, DNS-Auflösung und lokalen "
            "UDP-Kanal. Es wird noch keine BrandMeister-Anmeldung gesendet."
        )
    )
    parser.parse_args()

    try:
        config = NetworkConfigStore(CONFIG_PATH).load()
    except ValueError as exc:
        print(f"Netzwerkprüfung nicht möglich. {exc}")
        return 2

    print("\nCarenDMR Netzwerkdiagnose")
    print("-" * 40)
    results = NetworkDiagnostics(config).run()
    for result in results:
        label = {
            DiagnosticStatus.OK: "OK",
            DiagnosticStatus.WARNING: "Hinweis",
            DiagnosticStatus.ERROR: "Fehler",
        }[result.status]
        print(f"{label}: {result.spoken_text()}")

    if any(result.status is DiagnosticStatus.ERROR for result in results):
        return 2

    print(
        "\nNetzwerkgrundlage ist bereit. "
        "Es wurden keine Anmeldedaten übertragen."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
