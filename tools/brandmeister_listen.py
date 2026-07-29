"""One bounded, receive-only TG91/TS2 software-vocoder listening session."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from carendmr.brandmeister.config import BrandMeisterConfigStore
from carendmr.brandmeister.listen import listen_receive_only


CONFIG_PATH = PROJECT_ROOT / "config" / "brandmeister.local.json"
LISTEN_SECONDS = 60.0


def main() -> int:
    try:
        config = BrandMeisterConfigStore(CONFIG_PATH).load()
        print("Lokaler Audioweg wird kurz geprüft.")
        print("Danach beginnt ein rein empfangender TG91/TS2-Monitor.")
        result = listen_receive_only(config, seconds=LISTEN_SECONDS)
    except Exception as error:
        print(f"Empfang abgebrochen: {type(error).__name__}")
        print("Es wurde kein DMRD-Paket gesendet.")
        return 2

    print("Begrenzter Empfang beendet.")
    print(f"Authentifiziert: {'ja' if result.authenticated else 'nein'}")
    print(f"Audioausgabe gestartet: {'ja' if result.audio_started else 'nein'}")
    print(f"DMRD gesendet: 0")
    print(f"Datagramme empfangen: {result.datagrams}")
    print(f"TG91/TS2-Sprachbursts: {result.target_voice_bursts}")
    print(f"AMBE-Codewörter dekodiert: {result.decoded_codewords}")
    print(f"PCM-Samples ausgegeben: {result.decoded_samples}")
    print(f"Dekodierfehler: {result.decode_errors}")
    print(f"Korrigierte AMBE-Fehler: {result.corrected_errors}")
    print(f"Verdeckte fehlende Bursts: {result.concealed_bursts}")
    print(f"Ungültige DMRD: {result.invalid_dmrd}")
    print(f"Socket und Audio geschlossen: {'ja' if result.closed else 'nein'}")
    return 0 if result.authenticated and result.audio_started and result.closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
