from __future__ import annotations

import argparse
import platform
import sys
from pathlib import Path
from typing import Sequence

from carendmr.app_paths import default_data_root, is_frozen, prepare_data_root
from carendmr.brandmeister.config import BrandMeisterConfigStore
from carendmr.brandmeister.listen import (
    MAX_LISTEN_SECONDS,
    LiveCallActivity, LiveListenProgress,
    listen_receive_only,
)
from carendmr.config import ConfigError, load_config
from carendmr.logging_setup import configure_logging
from carendmr.version import __version__


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="CarenDMR",
        description="Barrierefreier BrandMeister-DMR-Client in Entwicklung.",
    )
    parser.add_argument(
        "--gui", "--gui-qt",
        action="store_true",
        help="öffnet die neue funktionale Qt-Betriebsoberfläche",
    )
    parser.add_argument(
        "--easy",
        action="store_true",
        help="öffnet die extrem reduzierte barrierefreie Easy-Oberfläche",
    )
    parser.add_argument(
        "--tg-monitor",
        action="store_true",
        help="öffnet nur den eigenständigen TG-Monitor",
    )
    parser.add_argument(
        "--listen",
        action="store_true",
        help=(
            "startet einen rein empfangenden TG91-/Timeslot-2-Livetest; "
            "ohne --duration läuft er bis Strg+C"
        ),
    )
    parser.add_argument(
        "--duration",
        type=float,
        metavar="SEKUNDEN",
        help=(
            "begrenzt --listen auf 1 bis 3600 Sekunden; "
            "ohne Angabe endet der Empfang mit Strg+C"
        ),
    )
    parser.add_argument(
        "--codec-benchmark",
        action="store_true",
        help="misst die Rechenzeit des Sprach-Codecs (CarenDMR.box, Raspberry Pi)",
    )
    parser.add_argument(
        "--frames",
        type=int,
        metavar="ANZAHL",
        help="Anzahl der 20-ms-Rahmen für --codec-benchmark (Vorgabe 1500 = 30 s)",
    )
    parser.add_argument(
        "--wav",
        type=Path,
        metavar="DATEI",
        help="eigenes Testsignal für --codec-benchmark (WAV, 8000 Hz, mono, 16 Bit)",
    )
    parser.add_argument(
        "--setup-codec",
        action="store_true",
        help="lädt für --codec-benchmark die MD380-Firmware, falls sie fehlt",
    )
    return parser


def _show_status(project_root: Path) -> int:
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
    print("Status              : Empfangsgrundlage bereit")
    print()
    print("Hinweis: BrandMeister-Login und DMR-Empfang sind implementiert.")
    print("Live-Empfang starten: python main.py --listen")
    print("Die allgemeine Bedienoberfläche und PTT sind noch nicht enthalten.")

    logger.info("CarenDMR Empfangsgrundlage ist bereit")
    return 0


def _print_progress(progress: LiveListenProgress) -> None:
    print(
        "Zwischenstand nach "
        f"{int(progress.elapsed_seconds)} s: "
        f"Datagramme {progress.datagrams}, "
        f"Sprachbursts {progress.target_voice_bursts}, "
        f"Dekodierfehler {progress.decode_errors}, "
        f"korrigierte Fehler {progress.corrected_errors}, "
        f"verdeckte Bursts {progress.concealed_bursts}, "
        f"ungültige DMRD {progress.invalid_dmrd}"
    )


def _print_call_activity(activity: LiveCallActivity) -> None:
    if activity.active:
        print(
            f"Neuer Sprecher: DMR-ID {activity.source_id}, "
            f"Talkgroup {activity.talkgroup}, Timeslot {activity.timeslot}."
        )
    else:
        print(f"Sprechdurchgang von DMR-ID {activity.source_id} beendet.")


def _run_live_listen(project_root: Path, *, seconds: float | None) -> int:
    config_path = project_root / "config" / "brandmeister.local.json"

    try:
        config = BrandMeisterConfigStore(config_path).load()
        print(f"CarenDMR {__version__} – TG91-Live-Empfang")
        print("-" * 52)
        print("Betriebsart: rein empfangend")
        print("Talkgroup:   91")
        print("Timeslot:    2")
        if seconds is None:
            print("Dauer:       unbegrenzt; Ende mit Strg+C")
        else:
            print(f"Dauer:       maximal {seconds:g} Sekunden")
        print("DMRD-Senden: technisch nicht vorgesehen")
        print()
        print("Der lokale Audioweg wird kurz geprüft.")
        print("Danach beginnt der Live-Empfang.")
        result = listen_receive_only(
            config,
            seconds=seconds,
            progress_callback=_print_progress,
            call_activity_callback=_print_call_activity,
        )
    except Exception as error:
        print(f"Live-Empfang abgebrochen: {type(error).__name__}: {error}", file=sys.stderr)
        print("Es wurde kein DMRD-Paket gesendet.", file=sys.stderr)
        return 2

    print()
    print("Live-Empfang beendet.")
    print(f"Beendigung:                {'Strg+C' if result.interrupted else 'Zeitgrenze'}")
    print(f"Laufzeit:                  {result.elapsed_seconds:.1f} Sekunden")
    print(f"Authentifiziert:            {'ja' if result.authenticated else 'nein'}")
    print(f"Audioausgabe gestartet:     {'ja' if result.audio_started else 'nein'}")
    print("DMRD gesendet:              0")
    print(f"Datagramme empfangen:       {result.datagrams}")
    print(f"TG91/TS2-Sprachbursts:      {result.target_voice_bursts}")
    print(f"AMBE-Codewörter dekodiert:  {result.decoded_codewords}")
    print(f"PCM-Samples ausgegeben:     {result.decoded_samples}")
    print(f"Dekodierfehler:             {result.decode_errors}")
    print(f"Korrigierte AMBE-Fehler:    {result.corrected_errors}")
    print(f"Verdeckte fehlende Bursts:  {result.concealed_bursts}")
    print(f"Ungültige DMRD:             {result.invalid_dmrd}")
    print(f"Socket und Audio geschlossen: {'ja' if result.closed else 'nein'}")

    return 0 if result.authenticated and result.audio_started and result.closed else 2


def run(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    # Ab 0.2.1.88: project_root ist der Datenordner. Beim Start aus dem
    # Quellcode ist das wie bisher das Projektverzeichnis, in der Exe
    # %LOCALAPPDATA%\CarenDMR (siehe carendmr/app_paths.py).
    project_root = default_data_root()
    prepare_data_root(project_root)

    if is_frozen() and not (args.gui or args.easy or args.listen or args.tg_monitor):
        # Die Exe hat keine Konsole; ohne Angabe öffnet sie das Hauptfenster.
        args.gui = True

    if args.tg_monitor and (args.gui or args.easy or args.listen):
        print("--tg-monitor kann nicht mit einer anderen Betriebsart kombiniert werden.", file=sys.stderr)
        return 2
    if (args.gui or args.easy) and args.listen:
        print("Eine GUI und --listen können nicht gleichzeitig verwendet werden.", file=sys.stderr)
        return 2
    if args.duration is not None and not args.listen:
        print("--duration ist nur zusammen mit --listen zulässig.", file=sys.stderr)
        return 2
    if args.duration is not None and not 1 <= args.duration <= MAX_LISTEN_SECONDS:
        print(
            f"--duration muss zwischen 1 und {int(MAX_LISTEN_SECONDS)} Sekunden liegen.",
            file=sys.stderr,
        )
        return 2
    benchmark_options = args.frames is not None or args.wav is not None or args.setup_codec
    if benchmark_options and not args.codec_benchmark:
        print("--frames, --wav und --setup-codec gehören zu --codec-benchmark.", file=sys.stderr)
        return 2
    if args.codec_benchmark:
        if args.gui or args.easy or args.listen or args.tg_monitor:
            print("--codec-benchmark kann nicht mit einer anderen Betriebsart kombiniert werden.", file=sys.stderr)
            return 2
        if args.frames is not None and not 100 <= args.frames <= 30000:
            print("--frames muss zwischen 100 und 30000 liegen.", file=sys.stderr)
            return 2
        from carendmr.box.codec_benchmark import DEFAULT_FRAMES, run_codec_benchmark_cli
        return run_codec_benchmark_cli(
            project_root,
            frames=args.frames or DEFAULT_FRAMES,
            wav=args.wav,
            setup_codec=args.setup_codec,
        )
    if args.tg_monitor:
        from carendmr.tg_monitor.window import run_tg_monitor
        return run_tg_monitor(project_root)
    if args.listen:
        return _run_live_listen(project_root, seconds=args.duration)
    if args.easy:
        from carendmr.ui_qt.easy_window import run_easy_gui
        return run_easy_gui(project_root)
    if args.gui:
        from carendmr.ui_qt import run_gui
        return run_gui(project_root)

    return _show_status(project_root)
