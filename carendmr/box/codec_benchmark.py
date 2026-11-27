"""Codec-Messung für CarenDMR.box (Qt-frei, ohne Zusatzpakete).

Misst, wie lange die MD380-Bridge für das Kodieren und Dekodieren eines
20-ms-Sprachrahmens braucht. Daraus folgt, ob ein Gerät (Raspberry Pi 4,
Zero 2 W …) genug Reserve für den Betrieb hat.

Start: ``python main.py --codec-benchmark``
"""
from __future__ import annotations

import math
import platform
import random
import statistics
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol, Sequence

FRAME_SAMPLES = 160
SAMPLE_RATE = 8000
FRAME_MS = 1000.0 * FRAME_SAMPLES / SAMPLE_RATE  # 20 ms
DEFAULT_FRAMES = 1500  # 30 Sekunden Sprache
WARMUP_FRAMES = 50  # dynarmic übersetzt beim ersten Durchlauf (JIT)

# Bewertung: Anteil des 20-ms-Rahmens, den Kodieren + Dekodieren im
# 99-%-Wert belegen. Der Rest bleibt für Netzwerk, Audio und Sprachausgabe.
GOOD_SHARE = 0.25
TIGHT_SHARE = 0.50


class FrameCodec(Protocol):
    def encode_2450x1150(self, pcm: tuple[int, ...]) -> bytes: ...

    def decode_2450x1150(self, ambe: bytes) -> tuple[int, ...]: ...


@dataclass(frozen=True)
class TimingStats:
    count: int
    mean_ms: float
    median_ms: float
    p95_ms: float
    p99_ms: float
    max_ms: float

    @classmethod
    def from_samples(cls, samples_ms: Sequence[float]) -> "TimingStats":
        if not samples_ms:
            raise ValueError("Keine Messwerte vorhanden.")
        ordered = sorted(samples_ms)
        return cls(
            count=len(ordered),
            mean_ms=statistics.fmean(ordered),
            median_ms=statistics.median(ordered),
            p95_ms=_percentile(ordered, 95.0),
            p99_ms=_percentile(ordered, 99.0),
            max_ms=ordered[-1],
        )


@dataclass(frozen=True)
class BenchmarkResult:
    encode: TimingStats
    decode: TimingStats
    cpu_temp_start_c: float | None
    cpu_temp_end_c: float | None

    @property
    def combined_p99_ms(self) -> float:
        return self.encode.p99_ms + self.decode.p99_ms

    @property
    def share_of_frame(self) -> float:
        return self.combined_p99_ms / FRAME_MS

    @property
    def verdict(self) -> str:
        share = self.share_of_frame
        if share <= GOOD_SHARE:
            return "gut"
        if share <= TIGHT_SHARE:
            return "knapp"
        return "zu langsam"


def _percentile(ordered: Sequence[float], percent: float) -> float:
    """Perzentil mit linearer Interpolation (Werte müssen sortiert sein)."""
    if len(ordered) == 1:
        return float(ordered[0])
    position = (len(ordered) - 1) * percent / 100.0
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[lower])
    weight = position - lower
    return float(ordered[lower] * (1.0 - weight) + ordered[upper] * weight)


def synthetic_speech_frames(count: int, *, seed: int = 2026) -> list[tuple[int, ...]]:
    """Erzeugt reproduzierbare, sprachähnliche Testrahmen (8 kHz, 16 Bit).

    Grundton mit Obertönen, wechselnder Tonhöhe, Silben-Hüllkurve und etwas
    Rauschen – genug, damit der Vocoder realistisch arbeitet.
    """
    if count < 1:
        raise ValueError("Es muss mindestens ein Rahmen erzeugt werden.")
    rng = random.Random(seed)
    frames: list[tuple[int, ...]] = []
    phase = 0.0
    for frame_index in range(count):
        pitch = 110.0 + 60.0 * math.sin(frame_index / 37.0)
        envelope = 0.15 + 0.85 * abs(math.sin(frame_index / 9.0))
        samples = []
        for _ in range(FRAME_SAMPLES):
            phase += 2.0 * math.pi * pitch / SAMPLE_RATE
            value = (
                math.sin(phase)
                + 0.5 * math.sin(2.0 * phase)
                + 0.25 * math.sin(3.0 * phase)
                + 0.12 * math.sin(5.0 * phase)
            ) / 1.87
            value = value * envelope + rng.uniform(-0.03, 0.03)
            samples.append(max(-32768, min(32767, int(round(value * 12000)))))
        frames.append(tuple(samples))
    return frames


def wav_frames(path: Path, *, max_frames: int | None = None) -> list[tuple[int, ...]]:
    """Liest eine WAV-Datei (8 kHz, mono, 16 Bit) in 160-Sample-Rahmen."""
    with wave.open(str(path), "rb") as handle:
        if handle.getframerate() != SAMPLE_RATE or handle.getnchannels() != 1 or handle.getsampwidth() != 2:
            raise ValueError(
                "Die WAV-Datei muss 8000 Hz, mono und 16 Bit haben "
                f"(gefunden: {handle.getframerate()} Hz, {handle.getnchannels()} Kanal/Kanäle, "
                f"{8 * handle.getsampwidth()} Bit)."
            )
        raw = handle.readframes(handle.getnframes())
    values = [
        int.from_bytes(raw[index:index + 2], "little", signed=True)
        for index in range(0, len(raw) - 1, 2)
    ]
    frames = [
        tuple(values[start:start + FRAME_SAMPLES])
        for start in range(0, len(values) - FRAME_SAMPLES + 1, FRAME_SAMPLES)
    ]
    if max_frames is not None:
        frames = frames[:max_frames]
    if not frames:
        raise ValueError("Die WAV-Datei ist kürzer als ein Sprachrahmen (20 ms).")
    return frames


def cpu_temperature_c(path: Path = Path("/sys/class/thermal/thermal_zone0/temp")) -> float | None:
    """CPU-Temperatur des Raspberry Pi in °C, sonst ``None``."""
    try:
        return int(path.read_text(encoding="ascii").strip()) / 1000.0
    except (OSError, ValueError):
        return None


def run_benchmark(
    codec: FrameCodec,
    frames: Sequence[tuple[int, ...]],
    *,
    warmup_frames: int = WARMUP_FRAMES,
    clock: Callable[[], float] = time.perf_counter,
    temperature: Callable[[], float | None] = cpu_temperature_c,
    progress: Callable[[int, int], None] | None = None,
) -> BenchmarkResult:
    """Kodiert und dekodiert jeden Rahmen und misst beide Zeiten."""
    if not frames:
        raise ValueError("Keine Testrahmen vorhanden.")
    for frame in frames[:warmup_frames]:
        codec.decode_2450x1150(codec.encode_2450x1150(frame))

    temp_start = temperature()
    encode_ms: list[float] = []
    decode_ms: list[float] = []
    total = len(frames)
    for index, frame in enumerate(frames, start=1):
        started = clock()
        ambe = codec.encode_2450x1150(frame)
        encoded = clock()
        codec.decode_2450x1150(ambe)
        decoded = clock()
        encode_ms.append((encoded - started) * 1000.0)
        decode_ms.append((decoded - encoded) * 1000.0)
        if progress is not None and (index % 250 == 0 or index == total):
            progress(index, total)
    return BenchmarkResult(
        encode=TimingStats.from_samples(encode_ms),
        decode=TimingStats.from_samples(decode_ms),
        cpu_temp_start_c=temp_start,
        cpu_temp_end_c=temperature(),
    )


def device_description() -> str:
    """Modell des Raspberry Pi (falls vorhanden), sonst Plattform."""
    model_path = Path("/proc/device-tree/model")
    try:
        model = model_path.read_bytes().rstrip(b"\x00").decode("utf-8", errors="replace").strip()
    except OSError:
        model = ""
    machine = platform.machine()
    return f"{model} ({machine})" if model else f"{platform.system()} {platform.release()} ({machine})"


def format_report(result: BenchmarkResult, *, device: str, source: str) -> str:
    def row(label: str, stats: TimingStats) -> str:
        return (
            f"{label:<12} Mittel {stats.mean_ms:6.2f} ms  Median {stats.median_ms:6.2f} ms  "
            f"95 % {stats.p95_ms:6.2f} ms  99 % {stats.p99_ms:6.2f} ms  Max {stats.max_ms:6.2f} ms"
        )

    def temp(value: float | None) -> str:
        return "unbekannt" if value is None else f"{value:.1f} °C"

    lines = [
        "CarenDMR Codec-Messung",
        "-" * 40,
        f"Gerät        : {device}",
        f"Testsignal   : {source}",
        f"Rahmen       : {result.encode.count} zu je {FRAME_MS:.0f} ms",
        row("Kodieren", result.encode),
        row("Dekodieren", result.decode),
        f"Beide (99 %) : {result.combined_p99_ms:.2f} ms = "
        f"{100.0 * result.share_of_frame:.1f} % eines 20-ms-Rahmens",
        f"CPU-Temperatur: Start {temp(result.cpu_temp_start_c)}, Ende {temp(result.cpu_temp_end_c)}",
        f"Bewertung    : {result.verdict}",
    ]
    if result.verdict == "gut":
        lines.append("Genug Reserve für Netzwerk, Audio und Sprachausgabe.")
    elif result.verdict == "knapp":
        lines.append("Läuft, aber mit wenig Reserve. Unter Last (Sprachausgabe, WLAN) prüfen.")
    else:
        lines.append("Zu langsam für zuverlässigen Betrieb. Stärkeres Gerät verwenden.")
    return "\n".join(lines)


def run_codec_benchmark_cli(
    project_root: Path,
    *,
    frames: int = DEFAULT_FRAMES,
    wav: Path | None = None,
    setup_codec: bool = False,
) -> int:
    """Konsolen-Ablauf für ``python main.py --codec-benchmark``."""
    from carendmr.application.codec_setup_service import CodecSetupError, CodecSetupService
    from carendmr.encoder.md380_dynarmic import Md380DynarmicEncoder

    setup = CodecSetupService(project_root)
    report = setup.status()
    if not report.ready and setup_codec and setup.bridge_path.is_file():
        print("Sprach-Codec wird eingerichtet …")
        try:
            report = setup.download_and_install(progress=print)
        except (CodecSetupError, OSError, RuntimeError) as error:
            print(f"Einrichtung fehlgeschlagen: {error}")
            return 2
    if not report.ready:
        print(report.message)
        if not setup.bridge_path.is_file():
            print("Bridge bauen: ./native/build_md380_dynarmic_linux.sh")
        else:
            print("Firmware laden: python main.py --codec-benchmark --setup-codec")
        return 2

    try:
        if wav is not None:
            test_frames = wav_frames(wav, max_frames=frames)
            source = f"{wav.name} ({len(test_frames)} Rahmen)"
        else:
            test_frames = synthetic_speech_frames(frames)
            source = "synthetisches Sprachsignal"
    except (OSError, ValueError, wave.Error) as error:
        print(f"Testsignal nicht nutzbar: {error}")
        return 2

    try:
        codec = Md380DynarmicEncoder(project_root)
    except RuntimeError as error:
        print(str(error))
        return 2
    try:
        print(f"Messung läuft ({len(test_frames)} Rahmen) …")
        result = run_benchmark(
            codec,
            test_frames,
            progress=lambda done, total: print(f"  {done}/{total}"),
        )
    finally:
        codec.close()
    print(format_report(result, device=device_description(), source=source))
    return 0
