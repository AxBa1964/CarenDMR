"""Einmaliger BrandMeister-Login-Test mit reproduzierbaren RPTC-Profiltests."""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from carendmr.version import get_version
from carendmr.network import PacketLogger
from carendmr.brandmeister import (
    BrandMeisterClient,
    BrandMeisterConfig,
    BrandMeisterConfigStore,
    BrandMeisterLoginError,
)

CONFIG_PATH = PROJECT_ROOT / "config" / "brandmeister.local.json"

REFERENCE_VALUES = {
    "latitude": 52.36999,
    "longitude": 10.47,
    "location": "JO52FI",
    "description": "",
    "frequency_hz": 438_800_000,
    "url": "www.qrz.com",
    "software_id": "20181107_Pi-Star",
    "package_id": "MMDVM_MMDVM_HS_Hat",
}


def build_reference_config(config: BrandMeisterConfig) -> BrandMeisterConfig:
    """Übernimmt Zugangsdaten und setzt die akzeptierten DroidStar-RPTC-Werte."""
    return replace(config, **REFERENCE_VALUES)


def build_test_config(
    local_config: BrandMeisterConfig,
    *,
    profile: str,
    software: bool = False,
    package: bool = False,
    description: bool = False,
    url: bool = False,
    software_value: str | None = None,
    package_value: str | None = None,
) -> tuple[BrandMeisterConfig, list[str]]:
    """Erzeugt das gewünschte Profil und nennt gezielt geänderte Referenzfelder."""
    if profile == "local":
        return local_config, ["vollständiges lokales CarenDMR-Profil"]

    config = build_reference_config(local_config)
    changed: list[str] = []
    replacements: dict[str, object] = {}

    if software_value is not None:
        replacements["software_id"] = software_value
        changed.append(f"Software-ID = {software_value!r}")
    elif software:
        replacements["software_id"] = local_config.software_id
        changed.append("Software-ID")

    if package_value is not None:
        replacements["package_id"] = package_value
        changed.append(f"Package-ID = {package_value!r}")
    elif package:
        replacements["package_id"] = local_config.package_id
        changed.append("Package-ID")
    if description:
        replacements["description"] = local_config.description
        changed.append("Beschreibung")
    if url:
        replacements["url"] = local_config.url
        changed.append("URL")

    if replacements:
        config = replace(config, **replacements)
    return config, changed


def print_profile(config: BrandMeisterConfig, changed: list[str], profile: str) -> None:
    print("\n" + "=" * 72)
    print("RPTC-Profil")
    print("=" * 72)
    print(f"Profil:       {'DroidStar-Referenz' if profile == 'reference' else 'lokale Konfiguration'}")
    print(f"Rufzeichen:   {config.callsign}")
    print(f"Frequenz:     {config.frequency_hz}")
    print(f"Breitengrad:  {config.latitude}")
    print(f"Längengrad:   {config.longitude}")
    print(f"Locator:      {config.location!r}")
    print(f"Beschreibung: {config.description!r}")
    print(f"URL:          {config.url!r}")
    print(f"Software:     {config.software_id!r}")
    print(f"Package:      {config.package_id!r}")
    print("Geänderte Referenzfelder:")
    if changed:
        for item in changed:
            print(f"  - {item}")
    else:
        print("  - keine")
    print("=" * 72)


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Meldet CarenDMR einmalig am BrandMeister-Master an. Das lokale Profil "
            "ist Standard; mit --profile reference werden reproduzierbare "
            "DroidStar-Vergleichstests durchgeführt."
        )
    )
    parser.add_argument(
        "--profile",
        choices=("local", "reference"),
        default="local",
        help="RPTC-Profil: lokale Konfiguration (Standard) oder DroidStar-Referenz.",
    )
    parser.add_argument("--software", action="store_true", help="Im Referenzprofil nur die lokale Software-ID einsetzen.")
    parser.add_argument("--package", action="store_true", help="Im Referenzprofil nur die lokale Package-ID einsetzen.")
    parser.add_argument(
        "--software-value",
        metavar="TEXT",
        help="Im Referenzprofil einen frei gewählten Software-ID-Wert testen.",
    )
    parser.add_argument(
        "--package-value",
        metavar="TEXT",
        help="Im Referenzprofil einen frei gewählten Package-ID-Wert testen.",
    )
    parser.add_argument("--description", action="store_true", help="Im Referenzprofil nur die lokale Beschreibung einsetzen.")
    parser.add_argument("--url", action="store_true", help="Im Referenzprofil nur die lokale URL einsetzen.")
    parser.add_argument(
        "--login-only",
        action="store_true",
        help="Nach der Anmeldung keinen RPTPING/MSTPONG-Test durchführen.",
    )
    parser.add_argument(
        "--no-packet-dump",
        action="store_true",
        help="Hex-/ASCII-Ausgabe der gesendeten und empfangenen Pakete abschalten.",
    )
    return parser


def main() -> int:
    parser = create_parser()
    args = parser.parse_args()

    field_test_requested = any(
        (
            args.software,
            args.package,
            args.description,
            args.url,
            args.software_value is not None,
            args.package_value is not None,
        )
    )
    if field_test_requested and args.profile != "reference":
        parser.error("Die Feldtests benötigen zusätzlich --profile reference.")
    if args.software and args.software_value is not None:
        parser.error("--software und --software-value dürfen nicht gemeinsam verwendet werden.")
    if args.package and args.package_value is not None:
        parser.error("--package und --package-value dürfen nicht gemeinsam verwendet werden.")

    try:
        local_config = BrandMeisterConfigStore(CONFIG_PATH).load()
    except ValueError as exc:
        print(f"BrandMeister-Prüfung nicht möglich. {exc}")
        return 2

    config, changed = build_test_config(
        local_config,
        profile=args.profile,
        software=args.software,
        package=args.package,
        description=args.description,
        url=args.url,
        software_value=args.software_value,
        package_value=args.package_value,
    )

    print(f"\nCarenDMR {get_version()} – BrandMeister-Anmeldung")
    print("-" * 52)
    print(f"Server:      {config.host}:{config.port}")
    print(f"DMR-ID:      {config.dmr_id}")
    print(f"Rufzeichen:  {config.callsign}")
    print("Passwort:    gespeichert, wird nicht angezeigt")
    print_profile(config, changed, args.profile)
    print("Anmeldung wird durchgeführt ...")

    packet_logger = PacketLogger(enabled=not args.no_packet_dump)
    client = BrandMeisterClient(config, packet_logger=packet_logger)
    try:
        result = client.login()
        print("OK: BrandMeister-Anmeldung erfolgreich.")
        print(f"Aufgelöste Adresse: {result.address}")

        if not args.login_only:
            print("RPTPING wird gesendet ...")
            if not client.ping():
                print("Fehler: Es wurde keine passende MSTPONG-Antwort empfangen.")
                return 2
            print("OK: MSTPONG empfangen.")

        print("Verbindung wird ordentlich geschlossen ...")
        return 0
    except BrandMeisterLoginError as exc:
        print(f"Anmeldung fehlgeschlagen: {exc}")
        return 2
    except OSError as exc:
        print(f"Netzwerkfehler: {exc}")
        return 2
    finally:
        client.close()
        print("UDP-Kanal geschlossen.")


if __name__ == "__main__":
    raise SystemExit(main())
