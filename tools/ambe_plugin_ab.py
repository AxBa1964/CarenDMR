"""Offline-A/B-Vergleich zweier DroidStar-kompatibler Vocoder-Builds.

Ziel 0.2.1.17:
- identische 8-kHz/PCM16/Mono-Referenz
- identischer fester Eingangspegel (+1 dB, bester bisheriger Hörpunkt)
- zwei verschiedene Windows-Vocoder-Binaries als Encoder A/B
- identischer CarenDMR/mbelib-Decoder für beide Pfade
- kein Netzwerk, kein TX, kein Parrot
"""
from __future__ import annotations

import argparse
import array
import hashlib
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
FIXED_GAIN_DB = 1.0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    peak = max(abs(value) for value in samples)
    mean_square = sum(float(value) * float(value) for value in samples) / len(samples)
    rms = math.sqrt(mean_square)
    return {
        "samples": len(samples),
        "rms_dbfs": round(20.0 * math.log10(max(rms / 32768.0, 1e-12)), 3),
        "peak_dbfs": round(20.0 * math.log10(max(peak / 32768.0, 1e-12)), 3),
        "peak": int(peak),
    }


def apply_fixed_gain(samples: list[int]) -> list[int]:
    factor = 10.0 ** (FIXED_GAIN_DB / 20.0)
    projected_peak = max((abs(value) for value in samples), default=0) * factor
    if projected_peak > 32767.0:
        raise RuntimeError("+1 dB würde die Referenz übersteuern; A/B-Test abgebrochen.")
    return [int(round(value * factor)) for value in samples]


def encode_decode(plugin: Path, pcm: list[int]) -> tuple[list[int], dict]:
    decoded_pcm: list[int] = []
    codewords: list[bytes] = []
    corrected = 0
    with DroidStarPluginEncoder(PROJECT_ROOT, plugin) as vocoder, NativeMbeReceiveVocoder() as mbe:
        for pos in range(0, len(pcm), FRAME):
            frame = pcm[pos:pos + FRAME]
            if len(frame) < FRAME:
                frame += [0] * (FRAME - len(frame))
            codeword = vocoder.encode_2450x1150(tuple(frame))
            codewords.append(codeword)
            decoded = mbe.decode(codeword)
            decoded_pcm.extend(decoded.samples)
            corrected += max(0, decoded.corrected_errors)
    ambe_bytes = b"".join(codewords)
    return decoded_pcm[:len(pcm)], {
        "ambe_frames": len(codewords),
        "ambe_sha256": hashlib.sha256(ambe_bytes).hexdigest(),
        "mbelib_corrected_bits": corrected,
    }


def resolve_plugin_a(explicit: Path | None) -> Path:
    if explicit is not None:
        path = explicit.expanduser().resolve()
    else:
        detected = EncoderService(PROJECT_ROOT).detect_plugin()
        if detected is None:
            raise RuntimeError("Aktuelles Vocoder-Plugin A konnte nicht eindeutig erkannt werden.")
        path = detected.resolve()
    if not path.is_file():
        raise RuntimeError(f"Plugin A fehlt: {path}")
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("wav", type=Path, help="10/10-Referenz: 03_vor_ambe_8k.wav")
    parser.add_argument("--plugin-a", type=Path, help="Optional: aktuelles Plugin A; sonst automatische Erkennung")
    parser.add_argument("--plugin-b", type=Path, required=True, help="Alternativer Windows-Vocoder-Build B")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    source = args.wav.expanduser().resolve()
    rate, original = read_wav(source)
    if rate != 8000:
        raise RuntimeError(f"Erwartet 8000 Hz, erhalten {rate} Hz.")

    plugin_a = resolve_plugin_a(args.plugin_a)
    plugin_b = args.plugin_b.expanduser().resolve()
    if not plugin_b.is_file():
        raise RuntimeError(f"Plugin B fehlt: {plugin_b}")

    if sha256_file(plugin_a) == sha256_file(plugin_b):
        print("HINWEIS: Plugin A und B sind byte-identisch. Der Hörvergleich bleibt deterministisch, kann aber keinen Build-Unterschied zeigen.")

    pcm = apply_fixed_gain(original)
    out = (args.out or source.parent / "ambe_plugin_ab").resolve()
    out.mkdir(parents=True, exist_ok=True)

    write_wav(out / "00_referenz_10von10_vor_ambe_8k.wav", rate, original)
    write_wav(out / "01_encoder_eingang_plus_01dB_8k.wav", rate, pcm)

    loop_a, info_a = encode_decode(plugin_a, pcm)
    loop_b, info_b = encode_decode(plugin_b, pcm)
    write_wav(out / "02_plugin_A_loopback_8k.wav", rate, loop_a)
    write_wav(out / "03_plugin_B_loopback_8k.wav", rate, loop_b)

    report = {
        "source": str(source),
        "sample_rate_hz": rate,
        "fixed_gain_db": FIXED_GAIN_DB,
        "reference_stats": stats(original),
        "encoder_input_stats": stats(pcm),
        "plugin_a": {
            "path": str(plugin_a),
            "size_bytes": plugin_a.stat().st_size,
            "sha256": sha256_file(plugin_a),
            "loopback_stats": stats(loop_a),
            **info_a,
        },
        "plugin_b": {
            "path": str(plugin_b),
            "size_bytes": plugin_b.stat().st_size,
            "sha256": sha256_file(plugin_b),
            "loopback_stats": stats(loop_b),
            **info_b,
        },
        "same_plugin_binary": sha256_file(plugin_a) == sha256_file(plugin_b),
        "same_ambe_output": info_a["ambe_sha256"] == info_b["ambe_sha256"],
        "files": {
            "reference": "00_referenz_10von10_vor_ambe_8k.wav",
            "encoder_input": "01_encoder_eingang_plus_01dB_8k.wav",
            "plugin_a": "02_plugin_A_loopback_8k.wav",
            "plugin_b": "03_plugin_B_loopback_8k.wav",
        },
    }
    (out / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"A/B-Test fertig: {out}")
    print(f"Plugin A SHA-256: {report['plugin_a']['sha256']}")
    print(f"Plugin B SHA-256: {report['plugin_b']['sha256']}")
    print(f"AMBE-Ausgabe identisch: {report['same_ambe_output']}")
    print("Hörfolge: 00 Referenz -> 01 Encoder-Eingang -> 02 Plugin A -> 03 Plugin B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
