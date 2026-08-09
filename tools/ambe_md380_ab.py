"""Offline-A/B: bisheriger Software-Vocoder gegen DroidStar-MD380-Pfad."""
from __future__ import annotations

import argparse, array, hashlib, json, math, sys, wave
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from carendmr.application.encoder_service import EncoderService
from carendmr.encoder import DroidStarPluginEncoder
from carendmr.encoder.md380_dynarmic import Md380DynarmicEncoder
from carendmr.vocoder.native import NativeMbeReceiveVocoder

FRAME = 160
FIXED_GAIN_DB = 1.0


def read_wav(path: Path):
    with wave.open(str(path), "rb") as w:
        if w.getnchannels() != 1 or w.getsampwidth() != 2 or w.getframerate() != 8000:
            raise RuntimeError("Eingang muss PCM16 mono mit 8000 Hz sein.")
        raw = w.readframes(w.getnframes())
    a = array.array("h"); a.frombytes(raw)
    if sys.byteorder != "little": a.byteswap()
    return list(a)


def write_wav(path: Path, samples: list[int]):
    a = array.array("h", samples)
    if sys.byteorder != "little": a.byteswap()
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000); w.writeframes(a.tobytes())


def gain(samples: list[int]) -> list[int]:
    factor = 10.0 ** (FIXED_GAIN_DB / 20.0)
    if max((abs(x) for x in samples), default=0) * factor > 32767:
        raise RuntimeError("+1 dB würde clippen.")
    return [int(round(x * factor)) for x in samples]


def stats(samples):
    peak = max((abs(x) for x in samples), default=0)
    rms = math.sqrt(sum(float(x)*x for x in samples)/max(1,len(samples)))
    return {"rms_dbfs": round(20*math.log10(max(rms/32768,1e-12)),3),
            "peak_dbfs": round(20*math.log10(max(peak/32768,1e-12)),3)}


def run_encoder(encoder, pcm):
    out=[]; ambe=[]; corrected=0
    with NativeMbeReceiveVocoder() as mbe:
        for pos in range(0,len(pcm),FRAME):
            frame=pcm[pos:pos+FRAME]
            if len(frame)<FRAME: frame += [0]*(FRAME-len(frame))
            word=encoder.encode_2450x1150(tuple(frame)); ambe.append(word)
            decoded=mbe.decode(word); out.extend(decoded.samples)
            corrected += max(0, decoded.corrected_errors)
    blob=b"".join(ambe)
    return out[:len(pcm)], {"ambe_frames":len(ambe), "ambe_sha256":hashlib.sha256(blob).hexdigest(),
                            "mbelib_corrected_bits":corrected}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("wav", type=Path)
    ap.add_argument("--out", type=Path)
    args=ap.parse_args()
    source=args.wav.resolve(); original=read_wav(source); pcm=gain(original)
    plugin=EncoderService(PROJECT_ROOT).detect_plugin()
    if plugin is None: raise RuntimeError("Plugin A konnte nicht erkannt werden.")
    md380=Md380DynarmicEncoder(PROJECT_ROOT)
    out=(args.out or source.parent/"ambe_md380_ab").resolve(); out.mkdir(parents=True,exist_ok=True)
    write_wav(out/"00_referenz_10von10_vor_ambe_8k.wav", original)
    write_wav(out/"01_encoder_eingang_plus_01dB_8k.wav", pcm)
    with DroidStarPluginEncoder(PROJECT_ROOT, plugin) as a:
        loop_a, info_a=run_encoder(a, pcm)
    loop_b, info_b=run_encoder(md380, pcm)
    write_wav(out/"02_plugin_A_bisher_loopback_8k.wav", loop_a)
    write_wav(out/"03_md380_DroidStar_loopback_8k.wav", loop_b)
    report={"source":str(source),"gain_db":FIXED_GAIN_DB,"input_stats":stats(pcm),
            "plugin_a":str(plugin),"md380_bridge":str(md380.path),
            "plugin_a_info":info_a,"md380_info":info_b,
            "same_ambe_output":info_a["ambe_sha256"]==info_b["ambe_sha256"]}
    (out/"report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print(f"A/B-Test fertig: {out}")
    print(f"AMBE-Ausgabe identisch: {report['same_ambe_output']}")
    print("Hörfolge: 00 Referenz -> 01 Eingang -> 02 bisher -> 03 MD380")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
