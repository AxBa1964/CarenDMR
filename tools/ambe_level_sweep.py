"""Offline-Pegelsweep vor dem AMBE-Encoder.

Verwendet eine vorhandene 8-kHz/PCM16/Mono-WAV als feste Referenz.
Es wird NICHT gesendet und keine BrandMeister-Verbindung aufgebaut.

Für +1, +2, +3, +4 und +5 dB wird:
1. der PCM-Eingang skaliert,
2. Clipping vor dem Encoder geprüft,
3. mit dem realen DroidStar-AMBE-Plugin encodiert,
4. mit dem aktuellen CarenDMR/mbelib-Decoder decodiert,
5. eine direkt vergleichbare Loopback-WAV erzeugt.
"""
from __future__ import annotations

import argparse
import array
import json
import math
import sys
import wave
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from carendmr.application.encoder_service import EncoderService
from carendmr.encoder import DroidStarPluginEncoder
from carendmr.vocoder.native import NativeMbeReceiveVocoder

FRAME = 160
LEVELS_DB = (1.0, 2.0, 3.0, 4.0, 5.0)


def read_wav(path: Path) -> tuple[int, list[int]]:
    with wave.open(str(path), "rb") as handle:
        if handle.getnchannels() != 1 or handle.getsampwidth() != 2:
            raise RuntimeError("Eingang muss PCM16 mono sein.")
        rate = handle.getframerate()
        raw = handle.readframes(handle.getnframes())
    values = array.array("h")
    values.frombytes(raw)
    if sys.byteorder != "little":
        values.byteswap()
    return rate, list(values)


def write_wav(path: Path, rate: int, samples: list[int]) -> None:
    values = array.array("h", samples)
    if sys.byteorder != "little":
        values.byteswap()
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(values.tobytes())


def stats(samples: list[int]) -> dict[str, float | int]:
    if not samples:
        return {"samples": 0, "rms_dbfs": -120.0, "peak_dbfs": -120.0, "peak": 0}
    peak = max(abs(v) for v in samples)
    mean_square = sum(float(v) * float(v) for v in samples) / len(samples)
    rms = math.sqrt(mean_square)
    rms_dbfs = 20.0 * math.log10(max(rms / 32768.0, 1e-12))
    peak_dbfs = 20.0 * math.log10(max(peak / 32768.0, 1e-12))
    return {
        "samples": len(samples),
        "rms_dbfs": round(rms_dbfs, 3),
        "peak_dbfs": round(peak_dbfs, 3),
        "peak": int(peak),
    }


def scale_without_clipping(samples: list[int], requested_db: float) -> tuple[list[int], dict]:
    factor = 10.0 ** (requested_db / 20.0)
    projected_peak = max((abs(v) for v in samples), default=0) * factor
    clipping_risk = projected_peak > 32767.0

    if clipping_risk:
        return [], {
            "requested_gain_db": requested_db,
            "gain_factor": factor,
            "status": "SKIPPED_CLIPPING_RISK",
            "projected_peak": round(projected_peak, 1),
        }

    scaled = [int(round(v * factor)) for v in samples]
    return scaled, {
        "requested_gain_db": requested_db,
        "gain_factor": round(factor, 6),
        "status": "OK",
        "projected_peak": round(projected_peak, 1),
    }


def encode_decode(samples: list[int], project: Path, plugin: Path) -> tuple[list[int], dict]:
    decoded_pcm: list[int] = []
    words = 0
    corrected = 0

    with DroidStarPluginEncoder(project, plugin) as vocoder, NativeMbeReceiveVocoder() as mbe:
        for pos in range(0, len(samples), FRAME):
            frame = samples[pos:pos + FRAME]
            if len(frame) < FRAME:
                frame = frame + [0] * (FRAME - len(frame))
            codeword = vocoder.encode_2450x1150(tuple(frame))
            decoded = mbe.decode(codeword)
            decoded_pcm.extend(decoded.samples)
            corrected += max(0, decoded.corrected_errors)
            words += 1

    return decoded_pcm[:len(samples)], {
        "ambe_frames": words,
        "mbelib_corrected_bits": corrected,
    }


def label_for_gain(db: float) -> str:
    return f"plus_{int(db):02d}dB" if db > 0 else "original_00dB"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("wav", type=Path, help="Referenz-WAV, z. B. 03_vor_ambe_8k.wav")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    source = args.wav.resolve()
    rate, samples = read_wav(source)
    if rate != 8000:
        raise RuntimeError(f"Erwartet 8000 Hz, erhalten {rate} Hz.")

    plugin = EncoderService(PROJECT_ROOT).detect_plugin()
    if plugin is None:
        raise RuntimeError("Kein eindeutig konfiguriertes DroidStar-Vocoder-Plugin gefunden.")

    out = (args.out or source.parent / "ambe_level_fine_sweep").resolve()
    out.mkdir(parents=True, exist_ok=True)

    report = {
        "source": str(source),
        "plugin": str(plugin),
        "sample_rate_hz": rate,
        "source_stats": stats(samples),
        "levels": [],
    }

    for index, gain_db in enumerate(LEVELS_DB, start=1):
        label = label_for_gain(gain_db)
        scaled, gain_info = scale_without_clipping(samples, gain_db)
        row = {"index": index, **gain_info}

        if not scaled:
            row["input_stats"] = None
            row["loopback_stats"] = None
            row["file"] = None
            report["levels"].append(row)
            print(f"{gain_db:+.0f} dB übersprungen: Clipping-Risiko.")
            continue

        loopback, codec_info = encode_decode(scaled, PROJECT_ROOT, plugin)
        filename = f"{index:02d}_{label}_loopback_8k.wav"
        write_wav(out / filename, rate, loopback)

        row.update(codec_info)
        row["input_stats"] = stats(scaled)
        row["loopback_stats"] = stats(loopback)
        row["file"] = filename
        report["levels"].append(row)
        print(
            f"{gain_db:+.0f} dB -> {filename} | "
            f"Eingang RMS {row['input_stats']['rms_dbfs']:.2f} dBFS, "
            f"Peak {row['input_stats']['peak_dbfs']:.2f} dBFS"
        )

    reference_name = "00_referenz_10von10_vor_ambe_8k.wav"
    write_wav(out / reference_name, rate, samples)
    report["reference_file"] = reference_name

    (out / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\nAMBE-Pegel-Feinsweep fertig: {out}")
    print("Zuerst 00_referenz_10von10_vor_ambe_8k.wav anhören, danach die Loopback-Dateien.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
