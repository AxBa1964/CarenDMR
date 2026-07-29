"""Exactly one locked private BrandMeister Parrot test."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from carendmr.accessibility import MacOSSpeechOutput, ParrotTestAnnouncer
from carendmr.brandmeister.config import BrandMeisterConfigStore
from carendmr.brandmeister.parrot_live import (
    ParrotLiveError,
    execute_locked_parrot_once,
)


CONFIG_PATH = PROJECT_ROOT / "config" / "brandmeister.local.json"


def main() -> int:
    try:
        config = BrandMeisterConfigStore(CONFIG_PATH).load()
        announcer = ParrotTestAnnouncer(MacOSSpeechOutput())
        result = execute_locked_parrot_once(config, announcer=announcer)
    except ParrotLiveError as error:
        print(f"Parrot-Test sicher abgebrochen: {error.cause_name}")
        print(f"DMRD gesendet: {error.sent_packets}/8")
        print(f"Bereinigt: {'ja' if error.closed else 'nein'}")
        print("Keine Wiederholung wurde versucht.")
        return 2
    except Exception as error:
        print(f"Parrot-Test vor Übertragung abgebrochen: {type(error).__name__}")
        print("DMRD gesendet: 0/8")
        print("Keine Wiederholung wurde versucht.")
        return 2

    print("Verriegelter privater Parrot-Test beendet.")
    print(f"Authentifiziert: {'ja' if result.authenticated else 'nein'}")
    print(f"DMRD gesendet: {result.sent_packets}/8")
    print(f"Sendezeit: {result.transmit_elapsed_seconds:.3f} Sekunden")
    print(f"Echo-Sprachbursts: {result.echo_voice_bursts}")
    print(f"AMBE-Codewörter dekodiert: {result.decoded_codewords}")
    print(f"PCM-Samples ausgegeben: {result.output_samples}")
    print(f"Dekodierfehler: {result.decode_errors}")
    print(f"Ungültige DMRD: {result.invalid_dmrd}")
    print(f"Echo empfangen: {'ja' if result.echo_received else 'nein'}")
    print(f"Echo-Timeout: {'ja' if result.timed_out else 'nein'}")
    print(f"Socket, Decoder und Audio geschlossen: {'ja' if result.closed else 'nein'}")
    print("Keine Wiederholung wurde versucht.")
    return 0 if result.closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
