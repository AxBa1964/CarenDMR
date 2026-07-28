"""Einmaliger BrandMeister-Login-Test für CarenDMR 0.0.7."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from carendmr.brandmeister import (
    BrandMeisterClient,
    BrandMeisterConfigStore,
    BrandMeisterLoginError,
)


CONFIG_PATH = PROJECT_ROOT / "config" / "brandmeister.local.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Meldet CarenDMR einmalig am konfigurierten BrandMeister-Master an, "
            "prüft einen Ping und meldet sich anschließend wieder ab."
        )
    )
    parser.add_argument(
        "--login-only",
        action="store_true",
        help="Nach der Anmeldung keinen RPTPING/MSTPONG-Test durchführen.",
    )
    args = parser.parse_args()

    try:
        config = BrandMeisterConfigStore(CONFIG_PATH).load()
    except ValueError as exc:
        print(f"BrandMeister-Prüfung nicht möglich. {exc}")
        return 2

    print("\nCarenDMR 0.0.7 – BrandMeister-Anmeldung")
    print("-" * 52)
    print(f"Server:   {config.host}:{config.port}")
    print(f"DMR-ID:   {config.dmr_id}")
    print(f"Rufzeichen: {config.callsign}")
    print("Passwort: gespeichert, wird nicht angezeigt")
    print("\nAnmeldung wird durchgeführt ...")

    client = BrandMeisterClient(config)
    try:
        result = client.login()
        print("OK: BrandMeister-Anmeldung erfolgreich.")
        print(f"Aufgelöste Adresse: {result.address}")

        if not args.login_only:
            print("RPTPING wird gesendet ...")
            if not client.ping():
                print(
                    "Fehler: Es wurde keine passende MSTPONG-Antwort empfangen."
                )
                return 2
            print("OK: MSTPONG empfangen.")

        print("Verbindung wird ordentlich geschlossen ...")
        return 0
    except BrandMeisterLoginError as exc:
        print(f"Anmeldung fehlgeschlagen: {exc}")
        print(
            "Bitte prüfen Sie Servername, UDP-Port, DMR-ID und das in "
            "BrandMeister SelfCare gesetzte Hotspot Security Password."
        )
        return 2
    except OSError as exc:
        print(f"Netzwerkfehler: {exc}")
        return 2
    finally:
        client.close()
        print("UDP-Kanal geschlossen.")


if __name__ == "__main__":
    raise SystemExit(main())
