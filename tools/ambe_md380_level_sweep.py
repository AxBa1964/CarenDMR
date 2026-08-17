"""Offline-Hörtest: MD380/DroidStar-Vocoder bei fein abgestuften Eingangspegeln."""
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

from carendmr.encoder.md380_dynarmic import Md380DynarmicEncoder
from carendmr.vocoder.native import NativeMbeReceiveVocoder

FRAME = 160
LEVELS_DB = (-2.0, -1.0, 0.0, 1.0, 2.0, 3.0)


def read_wav(path: Path) -> list[int]:
    with wave.open(str(path), "rb") as w:
        if w.getnchannels() != 1 or w.getsampwidth() != 2 or w.getframerate() != 8000:
            raise RuntimeError("Eingang muss PCM16 mono mit 8000 Hz sein.")
        raw = w.readframes(w.getnframes())
    samples = array.array("h")
    samples.frombytes(raw)
    if sys.byteorder != "little":
        samples.byteswap()
    return list(samples)


def write_wav(path: Path, samples: list[int]) -> None:
    data = array.array("h", samples)
    if sys.byteorder != "little":
        data.byteswap()
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(data.tobytes())


def apply_gain(samples: list[int], gain_db: float) -> tuple[list[int], int]:
    factor = 10.0 ** (gain_db / 20.0)
    out: list[int] = []
    clipped = 0
    for sample in samples:
        value = int(round(sample * factor))
        if value > 32767:
            value = 32767
            clipped += 1
        elif value < -32768:
            value = -32768
            clipped += 1
        out.append(value)
    return out, clipped


def stats(samples: list[int]) -> dict[str, float]:
    peak = max((abs(x) for x in samples), default=0)
    rms = math.sqrt(sum(float(x) * x for x in samples) / max(1, len(samples)))
    return {
        "rms_dbfs": round(20.0 * math.log10(max(rms / 32768.0, 1e-12)), 3),
        "peak_dbfs": round(20.0 * math.log10(max(peak / 32768.0, 1e-12)), 3),
    }


def loopback(encoder: Md380DynarmicEncoder, pcm: list[int]) -> list[int]:
    decoded_all: list[int] = []
    with NativeMbeReceiveVocoder() as decoder:
        for pos in range(0, len(pcm), FRAME):
            frame = pcm[pos:pos + FRAME]
            if len(frame) < FRAME:
                frame += [0] * (FRAME - len(frame))
            word = encoder.encode_2450x1150(tuple(frame))
            decoded = decoder.decode(word)
            decoded_all.extend(int(v) for v in decoded.samples)
    return decoded_all[:len(pcm)]


def level_label(db: float) -> str:
    sign = "plus" if db > 0 else "minus" if db < 0 else "null"
    value = str(abs(db)).replace(".", "p")
    return f"{sign}_{value}dB"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("wav", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    source = args.wav.resolve()
    original = read_wav(source)
    out = (args.out or source.parent / "ambe_md380_level_sweep").resolve()
    out.mkdir(parents=True, exist_ok=True)

    write_wav(out / "00_referenz_10von10_vor_ambe_8k.wav", original)

    report = {
        "source": str(source),
        "levels_db": list(LEVELS_DB),
        "source_stats": stats(original),
        "variants": [],
    }

    encoder = Md380DynarmicEncoder(PROJECT_ROOT)
    try:
        for index, db in enumerate(LEVELS_DB, start=1):
            pcm, clipped = apply_gain(original, db)
            decoded = loopback(encoder, pcm)
            filename = f"{index:02d}_md380_{level_label(db)}_loopback_8k.wav"
            write_wav(out / filename, decoded)
            report["variants"].append({
                "index": index,
                "gain_db": db,
                "filename": filename,
                "input_stats": stats(pcm),
                "output_stats": stats(decoded),
                "clipped_input_samples": clipped,
            })
    finally:
        encoder.close()

    (out / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"MD380-Pegeltest fertig: {out}")
    print("Hörfolge:")
    print("00 = Referenz vor AMBE")
    for item in report["variants"]:
        print(f"{item['index']:02d} = {item['gain_db']:+.0f} dB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
