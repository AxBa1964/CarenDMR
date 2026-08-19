"""Manueller QSO-Mitschnitt aus den digitalen TX-/RX-PCM-Pfaden."""

from __future__ import annotations

import array
import threading
import time
from datetime import datetime
from pathlib import Path

from carendmr.diagnostics.wav_io import write_pcm16_mono


class QsoRecordingService:
    SAMPLE_RATE = 8000

    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root)
        self.output_dir = self.project_root / "Mitschnitte"
        self._lock = threading.Lock()
        self._active = False
        self._started_monotonic = 0.0
        self._samples = array.array("h")
        self._path: Path | None = None
        self._last_source = ""

    @property
    def is_active(self) -> bool:
        with self._lock:
            return self._active

    @property
    def current_path(self) -> Path | None:
        with self._lock:
            return self._path

    def start(self) -> Path:
        with self._lock:
            if self._active and self._path is not None:
                return self._path
            self.output_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            path = self.output_dir / f"Mitschnitt_{stamp}.wav"
            suffix = 2
            while path.exists():
                path = self.output_dir / f"Mitschnitt_{stamp}_{suffix}.wav"
                suffix += 1
            self._samples = array.array("h")
            self._started_monotonic = time.monotonic()
            self._path = path
            self._active = True
            self._last_source = ""
            return path

    def add_tx(self, samples) -> None:
        self._append(samples, "TX")

    def add_rx(self, samples) -> None:
        self._append(samples, "RX")

    def _append(self, samples, source: str) -> None:
        values = tuple(int(v) for v in samples)
        if not values:
            return
        with self._lock:
            if not self._active:
                return
            elapsed = max(0.0, time.monotonic() - self._started_monotonic)
            expected_position = int(round(elapsed * self.SAMPLE_RATE))
            # Reale Sprechpausen bleiben im Mitschnitt erhalten. Kleine
            # Callback-Jitterwerte werden nicht künstlich aufgeblasen.
            if expected_position > len(self._samples) + 160:
                self._samples.extend([0] * (expected_position - len(self._samples)))
            self._samples.extend(
                max(-32768, min(32767, value)) for value in values
            )
            self._last_source = source

    def stop(self) -> Path | None:
        with self._lock:
            if not self._active:
                return None
            self._active = False
            path = self._path
            samples = array.array("h", self._samples)
            self._samples = array.array("h")
            self._path = None
            self._last_source = ""
        if path is None:
            return None
        if not samples:
            # Eine bewusst gestartete, aber völlig leere Aufnahme erzeugt
            # keine nutzlose WAV-Datei.
            return None
        import sys
        if sys.byteorder != "little":
            samples.byteswap()
        write_pcm16_mono(path, self.SAMPLE_RATE, samples.tobytes())
        return path
