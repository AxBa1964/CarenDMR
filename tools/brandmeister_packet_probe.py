"""Diagnose the BrandMeister receive path without sending DMRD traffic."""

from __future__ import annotations

import sys
import time
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from carendmr.brandmeister.client import BrandMeisterClient
from carendmr.brandmeister.config import BrandMeisterConfigStore
from carendmr.brandmeister.dmrd import parse_dmrd_packet
from carendmr.network import NetworkReceiveTimeout, identify_ascii_packet

CONFIG_PATH = PROJECT_ROOT / "config" / "brandmeister.local.json"
PROBE_SECONDS = 60.0
HEARTBEAT_SECONDS = 5.0


def main() -> int:
    config = BrandMeisterConfigStore(CONFIG_PATH).load()
    client = BrandMeisterClient(config)
    counters: Counter[str] = Counter()
    dmrd_examples: set[tuple[int, int, int, bool, str]] = set()

    print("BrandMeister-Paketdiagnose startet.")
    print("Wichtig: DroidStar und andere Clients mit derselben DMR-ID vorher trennen.")
    print("Es werden keine DMRD-Pakete gesendet.")

    try:
        client.login()
        print("Anmeldung: erfolgreich")
        deadline = time.monotonic() + PROBE_SECONDS
        next_ping = time.monotonic() + HEARTBEAT_SECONDS

        while time.monotonic() < deadline:
            now = time.monotonic()
            if now >= next_ping:
                client.send_ping()
                next_ping = now + HEARTBEAT_SECONDS
            try:
                packet = client.transport.receive()
            except NetworkReceiveTimeout:
                counters["TIMEOUT"] += 1
                continue

            packet_type = identify_ascii_packet(packet)
            counters[packet_type] += 1
            if not packet.startswith(b"DMRD"):
                continue

            try:
                frame = parse_dmrd_packet(packet)
            except (TypeError, ValueError):
                counters["DMRD_UNGUELTIG"] += 1
                continue

            dmrd_examples.add(
                (
                    frame.source_id,
                    frame.destination_id,
                    frame.timeslot,
                    frame.private_call,
                    frame.frame_class.name,
                )
            )
    finally:
        client.close()

    print("\nErgebnis nach 60 Sekunden:")
    for name, count in sorted(counters.items()):
        print(f"{name}: {count}")

    if dmrd_examples:
        print("\nErkannte DMRD-Beispiele:")
        for source, destination, slot, private, frame_class in sorted(dmrd_examples):
            call_type = "Privat" if private else "Gruppe"
            print(
                f"Quelle={source} Ziel={destination} TS={slot} "
                f"Ruftyp={call_type} Klasse={frame_class}"
            )
    else:
        print("\nKeine DMRD-Pakete empfangen.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
