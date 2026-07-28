"""Interaktive Audio-Prüfung für CarenDMR 0.0.5.1."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ermöglicht sowohl
#   python -m tools.audio_check
# als auch
#   python tools\audio_check.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from carendmr.audio import (
    AudioDirection,
    AudioManager,
    SoundDeviceBackend,
)
from carendmr.diagnostics import AudioDiagnostics, DiagnosticStatus


CONFIG_PATH = PROJECT_ROOT / "config" / "audio.local.json"


def print_devices(manager: AudioManager) -> None:
    print("\nGefundene Mikrofone")
    print("-" * 40)
    inputs = manager.list_devices(AudioDirection.INPUT)
    if not inputs:
        print("Keine Mikrofone gefunden.")
    for number, device in enumerate(inputs, start=1):
        print(f"{number}. {device.display_name(AudioDirection.INPUT)}")

    print("\nGefundene Wiedergabegeräte")
    print("-" * 40)
    outputs = manager.list_devices(AudioDirection.OUTPUT)
    if not outputs:
        print("Keine Wiedergabegeräte gefunden.")
    for number, device in enumerate(outputs, start=1):
        print(f"{number}. {device.display_name(AudioDirection.OUTPUT)}")


def select_device(manager: AudioManager, direction: AudioDirection):
    devices = manager.list_devices(direction)
    if not devices:
        return None

    noun = (
        "Mikrofon"
        if direction is AudioDirection.INPUT
        else "Wiedergabegerät"
    )
    while True:
        raw = input(
            f"\n{noun} auswählen. Nummer eingeben oder Enter für Standard: "
        ).strip()
        if not raw:
            return manager.default_device(direction) or devices[0]
        try:
            selected = devices[int(raw) - 1]
        except (ValueError, IndexError):
            print("Ungültige Auswahl. Bitte eine angezeigte Nummer eingeben.")
            continue
        return selected


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audiogeräte erkennen, auswählen und lokal testen."
    )
    parser.add_argument(
        "--diagnose-only",
        action="store_true",
        help="Nur Geräte und Auswahl prüfen, keine Aufnahme starten.",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=4.0,
        help="Dauer der Testaufnahme in Sekunden; Standard: 4.",
    )
    args = parser.parse_args()

    manager = AudioManager(SoundDeviceBackend(), CONFIG_PATH)

    try:
        manager.scan()
    except Exception as exc:
        print(f"Audio-Prüfung nicht möglich. {exc}")
        return 2

    print_devices(manager)

    diagnostics = AudioDiagnostics(manager).run()
    print("\nDiagnose")
    print("-" * 40)
    for result in diagnostics:
        label = {
            DiagnosticStatus.OK: "OK",
            DiagnosticStatus.WARNING: "Hinweis",
            DiagnosticStatus.ERROR: "Fehler",
        }[result.status]
        print(f"{label}: {result.spoken_text()}")

    if any(result.status is DiagnosticStatus.ERROR for result in diagnostics):
        return 2

    input_device = select_device(manager, AudioDirection.INPUT)
    output_device = select_device(manager, AudioDirection.OUTPUT)
    if input_device is None or output_device is None:
        print("Audio-Test nicht möglich, weil ein benötigtes Gerät fehlt.")
        return 2

    manager.save_selection(input_device, output_device)
    print(
        f"\nGespeichertes Mikrofon: {input_device.name}\n"
        f"Gespeichertes Wiedergabegerät: {output_device.name}"
    )

    if args.diagnose_only:
        print("\nAudio-Diagnose abgeschlossen.")
        return 0

    answer = input(
        "\nLokalen Audiotest starten? "
        "Es werden einige Sekunden aufgenommen und wiedergegeben. [j/N]: "
    ).strip().casefold()
    if answer not in {"j", "ja", "y", "yes"}:
        print("Audiotest übersprungen. Die Geräteauswahl wurde gespeichert.")
        return 0

    try:
        print("\nAufnahme läuft. Bitte sprechen Sie jetzt.")
        manager.run_loopback_test(duration_seconds=args.duration)
        print("Wiedergabe abgeschlossen.")
    except Exception as exc:
        print(
            "Der Audiotest konnte nicht abgeschlossen werden. "
            f"{exc} Bitte prüfen Sie die ausgewählten Geräte."
        )
        return 2

    heard = input(
        "Konnten Sie Ihre Aufnahme hören? [j/N]: "
    ).strip().casefold()
    if heard in {"j", "ja", "y", "yes"}:
        print("Audio-Selbsttest erfolgreich.")
        return 0

    print(
        "Die Aufnahme war nicht hörbar. Bitte prüfen Sie Lautstärke, "
        "Mikrofonfreigabe und Geräteauswahl und wiederholen Sie den Test."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
