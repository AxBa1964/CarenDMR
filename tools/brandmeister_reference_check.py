"""BrandMeister-Referenztest mit den exakt mitgeschnittenen DroidStar-RPTC-Metadaten."""

from __future__ import annotations

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
    BrandMeisterConfigStore,
    BrandMeisterLoginError,
)

CONFIG_PATH = PROJECT_ROOT / "config" / "brandmeister.local.json"


def build_reference_config(config):
    """Übernimmt Zugangsdaten, ersetzt aber RPTC-Metadaten durch den Referenzmitschnitt."""
    return replace(
        config,
        latitude=52.36999,
        longitude=10.47,
        location="JO52FI",
        description="",
        frequency_hz=438_800_000,
        url="www.qrz.com",
        software_id="20181107_Pi-Star",
        package_id="MMDVM_MMDVM_HS_Hat",
    )


def main() -> int:
    try:
        config = BrandMeisterConfigStore(CONFIG_PATH).load()
    except ValueError as exc:
        print(f"BrandMeister-Referenztest nicht möglich. {exc}")
        return 2

    config = build_reference_config(config)
    print(f"\nCarenDMR {get_version()} – BrandMeister-Referenztest")
    print("-" * 58)
    print(f"Server:      {config.host}:{config.port}")
    print(f"DMR-ID:      {config.dmr_id}")
    print(f"Rufzeichen:  {config.callsign}")
    print("RPTC-Profil: exakter DroidStar-Mitschnitt vom 28.07.2026")
    print("Passwort:    aus lokaler Konfiguration, wird nicht angezeigt")

    client = BrandMeisterClient(config, packet_logger=PacketLogger(enabled=True))
    try:
        result = client.login()
        print("OK: BrandMeister hat das Referenz-RPTC bestätigt.")
        print(f"Aufgelöste Adresse: {result.address}")
        return 0
    except BrandMeisterLoginError as exc:
        print(f"Referenztest fehlgeschlagen: {exc}")
        return 2
    except OSError as exc:
        print(f"Netzwerkfehler: {exc}")
        return 2
    finally:
        client.close()
        print("UDP-Kanal geschlossen.")


if __name__ == "__main__":
    raise SystemExit(main())
