"""Fachlicher Zustandsverfolger für geführte Modulationstests.

Das Modul ist bewusst frei von Qt-Abhängigkeiten. Es beobachtet ausschließlich
abgeschlossene Audio-Testartefakte und schreibt einen nachvollziehbaren Status
in ``manifest.json``. Funkkern und Audioaufnahme werden nicht gesteuert.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import os
import time
from typing import Any


@dataclass(frozen=True)
class ModulationTestSnapshot:
    state: str
    message: str
    session_dir: Path | None = None
    ready_for_comparison: bool = False
    failed: bool = False


class ModulationTestTracker:
    """Verfolgt einen einzelnen, bereits gestarteten Audio-Test passiv."""

    def __init__(self, audio_root: Path) -> None:
        self.audio_root = Path(audio_root)
        self.known_dirs: set[str] = set()
        self.session_dir: Path | None = None
        self._rx_size: int | None = None
        self._stable_polls = 0

    def arm(self) -> ModulationTestSnapshot:
        self.known_dirs = self._audio_test_dirs()
        self.session_dir = None
        self._rx_size = None
        self._stable_polls = 0
        return ModulationTestSnapshot("prepared", "Parrot vorbereitet. Warte auf TX.")

    def abort(self, message: str = "Modulationstest abgebrochen.") -> ModulationTestSnapshot:
        """Schließt den aktuellen Test fachlich eindeutig als abgebrochen ab."""
        from carendmr.diagnostics.tx_rx_timing import mark as timing_mark

        timing_mark("AUDIO_TEST_ABORTED", message)
        self._write_manifest("aborted", message, ready=False)
        return ModulationTestSnapshot(
            "aborted", message, self.session_dir, ready_for_comparison=False, failed=True
        )

    def reset(self) -> None:
        self.known_dirs.clear()
        self.session_dir = None
        self._rx_size = None
        self._stable_polls = 0

    def poll(self) -> ModulationTestSnapshot:
        try:
            if self.session_dir is None:
                new_dirs = [Path(value) for value in self._audio_test_dirs() - self.known_dirs]
                new_dirs = [path for path in new_dirs if path.is_dir()]
                if not new_dirs:
                    return ModulationTestSnapshot("prepared", "Parrot vorbereitet. Warte auf TX.")
                self.session_dir = max(new_dirs, key=lambda path: path.stat().st_mtime)
                self._write_manifest("tx_captured", "TX-Aufnahme erkannt. Warte auf Parrot-Antwort.")

            session = self.session_dir
            loopback = session / "04_codec_loopback_8k.wav"
            analysis_file = session / "analysis.json"
            if not loopback.is_file():
                return self._snapshot("capturing_tx", "TX läuft beziehungsweise Codec-Loopback wird abgeschlossen.")
            if not analysis_file.is_file():
                return self._snapshot("waiting_analysis", "TX gespeichert. Warte auf Analyse und Parrot-Antwort.")

            payload = self._read_json(analysis_file)
            extra = payload.get("extra") or {}
            parrot_files = list(session.glob("rx_*_parrot_nach_ambe_8k.wav"))
            if not parrot_files:
                if extra.get("echo_received") is False:
                    return self._fail("Keine vollständige Parrot-Antwort empfangen.")
                return self._snapshot("waiting_parrot", "TX gespeichert. Warte auf Parrot-Antwort.")

            parrot = max(parrot_files, key=lambda path: path.stat().st_mtime)
            size = parrot.stat().st_size
            if size <= 44:
                return self._snapshot("capturing_parrot", "Parrot-Antwort wurde erkannt und wird aufgezeichnet.")
            if size != self._rx_size:
                self._rx_size = size
                self._stable_polls = 0
                return self._snapshot("capturing_parrot", "Parrot-Antwort wird vollständig empfangen.")
            self._stable_polls += 1
            if self._stable_polls < 2:
                return self._snapshot("finalizing", "Parrot-Antwort beendet. Dateien werden abgeschlossen.")

            # analysis.json muss nach dem RX-Abschluss ausdrücklich den Echo-Erfolg enthalten.
            payload = self._read_json(analysis_file)
            extra = payload.get("extra") or {}
            if extra.get("echo_received") is not True:
                return self._snapshot("finalizing", "Parrot-Datei liegt vor. Warte auf Abschluss der Analyse.")

            self._write_manifest("completed", "Modulationstest vollständig gespeichert.", ready=True)
            return ModulationTestSnapshot(
                "completed", "Modulationstest vollständig gespeichert.", session,
                ready_for_comparison=True,
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return self._fail(f"Modulationstest konnte nicht abgeschlossen werden: {exc}")

    def _audio_test_dirs(self) -> set[str]:
        if not self.audio_root.exists():
            return set()
        return {str(path.resolve()) for path in self.audio_root.glob("AudioTest_*") if path.is_dir()}

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _snapshot(self, state: str, message: str) -> ModulationTestSnapshot:
        self._write_manifest(state, message)
        return ModulationTestSnapshot(state, message, self.session_dir)

    def _fail(self, message: str) -> ModulationTestSnapshot:
        self._write_manifest("failed", message)
        return ModulationTestSnapshot("failed", message, self.session_dir, failed=True)

    def _write_manifest(self, state: str, message: str, *, ready: bool = False) -> None:
        if self.session_dir is None:
            return
        payload = {
            "version": 1,
            "state": state,
            "message": message,
            "ready_for_comparison": bool(ready),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "session_dir": str(self.session_dir),
        }
        target = self.session_dir / "manifest.json"
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        last_error: OSError | None = None
        for _attempt in range(6):
            try:
                os.replace(temporary, target)
                return
            except PermissionError as exc:
                last_error = exc
                time.sleep(0.1)
        if last_error is not None:
            # Die Messdaten bleiben vollständig erhalten; nur die Statusdatei
            # konnte wegen einer kurzfristigen Windows-/OneDrive-Sperre nicht
            # atomar ersetzt werden.
            fallback = self.session_dir / "manifest.pending.json"
            fallback.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
