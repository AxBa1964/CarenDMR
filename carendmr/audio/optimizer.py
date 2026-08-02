"""Plattformneutrale Sprachaufbereitung vor dem AMBE-Encoder."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OptimizerDiagnostics:
    input_peak_percent: float
    output_peak_percent: float
    gain_db: float
    clipped_samples: int


def optimize_transmit_pcm(samples: tuple[int, ...], *, sample_rate: int = 8000) -> tuple[tuple[int, ...], OptimizerDiagnostics]:
    """Optimiert Sprache dezent: DC-Sperre, Hochpass, Kompressor und Limiter.

    Die Funktion ist absichtlich deterministisch und verwendet nur NumPy. Sie
    verändert weder Ziel-ID noch DMR-Protokoll und ist auf allen Zielsystemen
    identisch.
    """
    if sample_rate != 8000:
        raise ValueError("Der DMR-Sprachoptimierer erwartet 8 kHz PCM.")
    if not samples:
        raise ValueError("Leere Sprache kann nicht optimiert werden.")

    import numpy as np

    x = np.asarray(samples, dtype=np.float64) / 32768.0
    input_peak = float(np.max(np.abs(x))) if x.size else 0.0

    # DC entfernen.
    x = x - float(np.mean(x))

    # Einpoliger Hochpass bei ungefähr 120 Hz.
    cutoff = 120.0
    dt = 1.0 / sample_rate
    rc = 1.0 / (2.0 * np.pi * cutoff)
    alpha = rc / (rc + dt)
    hp = np.empty_like(x)
    hp[0] = x[0]
    for i in range(1, x.size):
        hp[i] = alpha * (hp[i - 1] + x[i] - x[i - 1])

    # Sprachkompressor mit klar hörbarer, aber natürlicher Kennlinie
    # oberhalb -20 dBFS, Ratio 3:1.
    threshold = 10.0 ** (-20.0 / 20.0)
    magnitude = np.abs(hp)
    compressed_mag = np.where(
        magnitude <= threshold,
        magnitude,
        threshold + (magnitude - threshold) / 3.0,
    )
    compressed = np.sign(hp) * compressed_mag

    # Auf Sprachlautheit normieren. RMS ist für Sprache aussagekräftiger als
    # nur der einzelne Spitzenwert. Maximal +12 dB, damit leise Mikrofone
    # angehoben werden, ohne Raumrauschen grenzenlos hochzuziehen.
    rms = float(np.sqrt(np.mean(np.square(compressed)))) if compressed.size else 0.0
    target_rms = 10.0 ** (-18.0 / 20.0)
    max_gain = 10.0 ** (12.0 / 20.0)
    gain = 1.0 if rms <= 1e-9 else min(max_gain, target_rms / rms)
    adjusted = compressed * gain

    # Soft-Limiter statt hartem Clipping.
    limited = np.tanh(adjusted * 1.35) / np.tanh(1.35)
    clipped = int(np.count_nonzero(np.abs(adjusted) > 1.0))
    pcm = np.clip(np.rint(limited * 32767.0), -32768, 32767).astype(np.int16)
    output_peak = float(np.max(np.abs(pcm.astype(np.float64)))) / 32767.0
    gain_db = 20.0 * float(np.log10(max(gain, 1e-12)))
    return tuple(int(v) for v in pcm), OptimizerDiagnostics(
        input_peak_percent=input_peak * 100.0,
        output_peak_percent=output_peak * 100.0,
        gain_db=gain_db,
        clipped_samples=clipped,
    )
