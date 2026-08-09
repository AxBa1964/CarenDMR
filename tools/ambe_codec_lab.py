"""Offline-Hörvergleich der realen CarenDMR-AMBE-Kette.

Kein Netzwerk, kein BrandMeister, kein TX. Eingang ist eine vorhandene
03_vor_ambe_8k.wav. Es werden zwei Decoderpfade gegenübergestellt:
A) aktueller CarenDMR-RX-Decoder (mbelib)
B) dasselbe DroidStar-Vocoder-Plugin, das auch encodiert
"""
from __future__ import annotations
import argparse, array, json, sys, wave
from pathlib import Path

# Direkter Start aus .\tools muss die Projektwurzel in sys.path aufnehmen.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from carendmr.application.encoder_service import EncoderService
from carendmr.encoder import DroidStarPluginEncoder
from carendmr.vocoder.native import NativeMbeReceiveVocoder

FRAME = 160

def read_wav(path: Path) -> tuple[int, list[int]]:
    with wave.open(str(path), "rb") as w:
        if w.getnchannels()!=1 or w.getsampwidth()!=2:
            raise RuntimeError("Eingang muss PCM16 mono sein.")
        rate=w.getframerate()
        raw=w.readframes(w.getnframes())
    a=array.array("h"); a.frombytes(raw)
    if sys.byteorder!="little": a.byteswap()
    return rate, list(a)

def write_wav(path: Path, rate: int, samples: list[int]) -> None:
    a=array.array("h", (max(-32768,min(32767,int(x))) for x in samples))
    if sys.byteorder!="little": a.byteswap()
    with wave.open(str(path),"wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(a.tobytes())

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("wav", type=Path, help="03_vor_ambe_8k.wav")
    ap.add_argument("--out", type=Path)
    ns=ap.parse_args()
    src=ns.wav.resolve()
    rate,samples=read_wav(src)
    if rate!=8000: raise RuntimeError(f"Erwartet 8000 Hz, erhalten {rate} Hz.")
    project=PROJECT_ROOT
    plugin=EncoderService(project).detect_plugin()
    if plugin is None: raise RuntimeError("Kein eindeutig konfiguriertes DroidStar-Vocoder-Plugin gefunden.")
    out=(ns.out or src.parent/"ambe_codec_lab").resolve(); out.mkdir(parents=True,exist_ok=True)
    native=[]; plugin_pcm=[]; words=[]; corrected=0; frames=0
    with DroidStarPluginEncoder(project,plugin) as vocoder, NativeMbeReceiveVocoder() as mbe:
        for pos in range(0,len(samples),FRAME):
            frame=samples[pos:pos+FRAME]
            if len(frame)<FRAME: frame += [0]*(FRAME-len(frame))
            word=vocoder.encode_2450x1150(tuple(frame)); words.append(word)
            decoded=mbe.decode(word); native.extend(decoded.samples); corrected += max(0,decoded.corrected_errors)
            plugin_pcm.extend(vocoder.decode_2450x1150(word)); frames += 1
    write_wav(out/"01_eingang_vor_ambe_8k.wav",rate,samples)
    write_wav(out/"02_loopback_carendmr_mbelib_8k.wav",rate,native[:len(samples)])
    write_wav(out/"03_loopback_droidstar_plugin_8k.wav",rate,plugin_pcm[:len(samples)])
    (out/"04_ambe_frames.bin").write_bytes(b"".join(words))
    report={"source":str(src),"plugin":str(plugin),"frames":frames,
            "samples":len(samples),"mbelib_corrected_bits":corrected,
            "files":{"input":"01_eingang_vor_ambe_8k.wav",
                     "carendmr_mbelib":"02_loopback_carendmr_mbelib_8k.wav",
                     "droidstar_plugin":"03_loopback_droidstar_plugin_8k.wav"}}
    (out/"report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print(f"AMBE Codec Lab fertig: {out}")
    print("Hörfolge: 01 Eingang -> 02 CarenDMR/mbelib -> 03 DroidStar-Plugin")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
