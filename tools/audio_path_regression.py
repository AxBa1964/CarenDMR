from __future__ import annotations

import argparse
import json
import math
import struct
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from threading import Event

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from carendmr.application.audio_send_service import AudioSendService
from carendmr.application.encoder_service import EncoderService
from carendmr.audio import AudioDevice, BufferedPcmOutput, tuner_preset
from carendmr.brandmeister.config import BrandMeisterConfigStore
from carendmr.brandmeister.dmrd import DmrdCallType
from carendmr.brandmeister.live_voice_transmit import execute_live_voice_once
from carendmr.diagnostics.tx_rx_timing import (
    attach_session as timing_attach_session,
    detach_session as timing_detach_session,
    initialize as timing_initialize,
    mark as timing_mark,
    start_cycle as timing_start_cycle,
)


def _resample(data: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
    data = np.asarray(data, dtype=np.float32).reshape(-1)
    if source_rate == target_rate or not data.size:
        return data
    from math import gcd
    divisor = gcd(int(source_rate), int(target_rate))
    return np.asarray(
        resample_poly(data, int(target_rate) // divisor, int(source_rate) // divisor),
        dtype=np.float32,
    )


def _load_reference(path: Path) -> tuple[np.ndarray, int]:
    data, sample_rate = sf.read(path, dtype="float32", always_2d=True)
    # Dasselbe Verhalten wie ein Monomikrofon: bei Stereodateien beide Kanäle
    # gleich gewichtet auf Mono abbilden.
    mono = np.asarray(data.mean(axis=1), dtype=np.float32)
    return mono, int(sample_rate)


def _pcm16_from_float(samples: np.ndarray) -> tuple[int, ...]:
    pcm = np.clip(np.rint(np.clip(samples, -1.0, 1.0) * 32767.0), -32768, 32767)
    return tuple(int(v) for v in pcm.astype(np.int16))


def _level_metrics(samples) -> dict[str, float | int]:
    x = np.asarray(tuple(samples), dtype=np.float64)
    if not x.size:
        return {
            "samples": 0,
            "peak_percent": 0.0,
            "peak_dbfs": -120.0,
            "rms_dbfs": -120.0,
            "clipped_samples": 0,
        }
    # int16 und float [-1,1] akzeptieren.
    if float(np.max(np.abs(x))) > 1.5:
        normalized = x / 32768.0
        clipped = int(np.count_nonzero(np.abs(x) >= 32767.0))
    else:
        normalized = x
        clipped = int(np.count_nonzero(np.abs(x) >= 0.99997))
    peak = float(np.max(np.abs(normalized)))
    rms = float(np.sqrt(np.mean(np.square(normalized))))
    db_peak = 20.0 * math.log10(max(peak, 1e-6))
    db_rms = 20.0 * math.log10(max(rms, 1e-6))
    return {
        "samples": int(x.size),
        "peak_percent": round(peak * 100.0, 3),
        "peak_dbfs": round(max(-120.0, db_peak), 3),
        "rms_dbfs": round(max(-120.0, db_rms), 3),
        "clipped_samples": clipped,
    }


class ReferenceAudioBackend:
    """Virtuelles Mikrofon für die produktive LivePcmCapture-Strecke.

    Nur die Hardwarequelle wird ersetzt. Mic-Gain, Sprachprozessor, Audio-Tuner,
    16->8-kHz-Decimator und der danach folgende AMBE-/DMR-Pfad bleiben produktiv.
    """

    def __init__(self, source: np.ndarray, source_rate: int) -> None:
        self.source = np.asarray(source, dtype=np.float32).reshape(-1)
        self.source_rate = int(source_rate)
        self.last_input_stream_info: dict[str, object] = {}

    def query_devices(self):
        return [
            AudioDevice(
                index=0,
                name="CarenDMR Referenz-MP3",
                host_api="Regression",
                max_input_channels=1,
                max_output_channels=0,
                default_sample_rate=16000.0,
                is_default_input=True,
            )
        ]

    def resolve_input_sample_rate(self, input_index: int, requested_rate: int, channels: int) -> int:
        return int(requested_rate)

    def stream_input_blocks_until(
        self, *, input_index: int, stop_event: Event, max_duration_seconds: float,
        sample_rate: int, channels: int, block_callback, level_callback=None,
    ) -> None:
        data = _resample(self.source, self.source_rate, int(sample_rate))
        limit = int(round(float(max_duration_seconds) * int(sample_rate)))
        data = data[:limit]
        callbacks = 0
        for start in range(0, len(data), 320):
            if stop_event.is_set():
                break
            block = data[start:start + 320].reshape(-1, 1)
            if not block.size:
                continue
            block_callback(block)
            callbacks += 1
            if level_callback is not None:
                rms = float(np.sqrt(np.mean(np.square(block, dtype=np.float64))))
                level_callback(min(100.0, rms * 200.0))
        self.last_input_stream_info = {
            "device_index": 0,
            "requested_rate": int(sample_rate),
            "native_rate": int(sample_rate),
            "channels": int(channels),
            "capture_channels": 1,
            "callbacks": callbacks,
            "native_samples": int(len(data)),
            "channel_peak": [float(np.max(np.abs(data))) if data.size else 0.0],
            "source": "reference-mp3",
        }


class MeasuringPcmOutput(BufferedPcmOutput):
    """Produktiver RX-Pegelfilter ohne physische Soundkarte.

    write() läuft durch BufferedPcmOutput.write() und anschließend durch exakt
    dessen _callback(). Damit werden dieselbe AGC-, RX-Volume-, Basisgain- und
    Limiterlogik wie bei der Soundkarte ausgeführt.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.raw_rx_samples: list[int] = []
        self.output_rx_samples: list[int] = []

    def start(self) -> None:
        # Keine Hardware öffnen. Die Callback-Verarbeitung wird in write()
        # synchron angestoßen.
        return None

    def write(self, samples) -> None:
        values = tuple(int(v) for v in samples)
        self.raw_rx_samples.extend(values)
        super().write(values)
        if not values:
            return
        out = bytearray(len(values) * 2)
        self._callback(memoryview(out), len(values), None, None)
        if out:
            self.output_rx_samples.extend(struct.unpack(f"<{len(values)}h", out))

    def close(self) -> None:
        with self._lock:
            self._buffer.clear()


def _make_audio_service(source: np.ndarray, source_rate: int, profile: str | None) -> AudioSendService:
    backend = ReferenceAudioBackend(source, source_rate)
    service = AudioSendService(ROOT, backend=backend)
    service._selected_input = backend.query_devices()[0]
    if profile:
        service.set_tx_audio_tuner_settings(tuner_preset(profile))
    service.set_audio_debug_wav_enabled(True)
    return service


def _run_case(path: Path, profile: str | None, outdir: Path, cfg, enc_service: EncoderService):
    source, source_rate = _load_reference(path)
    audio_service = _make_audio_service(source, source_rate, profile)
    stop_event = Event()
    duration = len(source) / float(source_rate)

    testdir = outdir / path.stem
    testdir.mkdir(parents=True, exist_ok=True)
    timing_start_cycle(f"AUDIO REGRESSION {path.name} Profil={audio_service.tx_audio_tuner_settings.profile}")
    timeline_path = timing_attach_session(testdir)

    timing_mark(
        "AUDIO_REGRESSION_START",
        f"Datei={path.name};QuelleHz={source_rate};Dauer={duration:.3f};"
        f"Profil={audio_service.tx_audio_tuner_settings.profile};"
        f"MicGain={audio_service.gain_percent};RXVolume={audio_service.output_volume_percent};"
        f"AGC={int(audio_service.agc_enabled)}",
    )

    # Das ist dieselbe produktive LivePcmCapture-Klasse, die Space-PTT benutzt.
    capture = audio_service.start_live_capture(
        stop_event,
        max_duration_seconds=max(5.0, min(300.0, duration + 2.0)),
    )

    output_holder: list[MeasuringPcmOutput] = []

    def output_factory(*, sample_rate=8000, **_kwargs):
        out = MeasuringPcmOutput(
            sample_rate=sample_rate,
            muted=lambda: audio_service.user_muted,
            volume=lambda: audio_service.output_volume_percent / 100.0,
            agc_enabled=lambda: audio_service.agc_enabled,
        )
        output_holder.append(out)
        return out

    encoder = enc_service.create_transmit_encoder()
    started = time.monotonic()
    try:
        result = execute_live_voice_once(
            cfg,
            destination_id=9990,
            timeslot=2,
            call_type=DmrdCallType.PRIVATE,
            pcm_chunks=capture.chunks(),
            encoder=encoder,
            wait_for_parrot_echo=True,
            lead_in_seconds=0.240,
            output_factory=output_factory,
        )
    finally:
        close = getattr(encoder, "close", None)
        if callable(close):
            close()

    out = output_holder[0] if output_holder else None
    if int(result.voice_bursts_sent) > 0 and not capture._ambe_pcm_8k:
        raise RuntimeError(
            "Audio-QS-Instrumentierung leer: DMR-Voice wurde gesendet, "
            "aber vor AMBE wurden keine Messsamples erfasst."
        )
    expected = max(1, int(result.voice_bursts_sent))
    completeness = 100.0 * int(result.echo_voice_bursts) / expected

    row = {
        "file": path.name,
        "profile": audio_service.tx_audio_tuner_settings.profile,
        "duration_s": round(duration, 3),
        "wall_s": round(time.monotonic() - started, 3),
        "settings": {
            "microphone_gain_percent": int(audio_service.gain_percent),
            "speech_processing_enabled": bool(audio_service.tx_speech_processing_enabled),
            "tx_audio_tuner": audio_service.tx_audio_tuner_settings.to_dict(),
            "rx_volume_percent": int(audio_service.output_volume_percent),
            "rx_agc_enabled": bool(audio_service.agc_enabled),
            "rx_muted": bool(audio_service.user_muted),
        },
        "dmr": {
            "voice_bursts_sent": int(result.voice_bursts_sent),
            "echo_voice_bursts": int(result.echo_voice_bursts),
            "echo_completeness_percent": round(completeness, 2),
            "echo_received": bool(result.echo_received),
            "timed_out": bool(result.timed_out),
            "decode_errors": int(result.decode_errors),
        },
        "levels": {
            "reference_source": _level_metrics(source),
            "mic_raw_16k": _level_metrics(capture._input_pcm_16k),
            "after_mic_gain_16k": _level_metrics(capture._gain_pcm_16k),
            "after_tx_processing_16k": _level_metrics(capture._processed_pcm_16k),
            "before_ambe_8k": _level_metrics(capture._ambe_pcm_8k),
            "rx_after_ambe_8k": _level_metrics(out.raw_rx_samples if out else ()),
            "rx_before_soundcard_8k": _level_metrics(out.output_rx_samples if out else ()),
        },
        "timeline": str(timeline_path.relative_to(ROOT)),
    }
    timing_mark(
        "AUDIO_REGRESSION_RESULT",
        f"Echo={row['dmr']['echo_completeness_percent']:.2f}%;"
        f"TXRMS={row['levels']['before_ambe_8k']['rms_dbfs']:.3f}dBFS;"
        f"RXDecodeRMS={row['levels']['rx_after_ambe_8k']['rms_dbfs']:.3f}dBFS;"
        f"RXOutRMS={row['levels']['rx_before_soundcard_8k']['rms_dbfs']:.3f}dBFS",
    )
    timing_detach_session()
    return row


def main() -> int:
    ap = argparse.ArgumentParser(
        description="CarenDMR Audio-End-to-End-Regression mit produktiver TX/RX-Soundstrecke"
    )
    ap.add_argument("--sound-dir", default=str(ROOT / "Sound"))
    ap.add_argument("--count", type=int, default=10)
    ap.add_argument(
        "--profile",
        choices=("all", "current", "Neutral", "Klar", "DX", "Warm"),
        default="all",
        help="TX-Audioprofil. Standard 'all' testet automatisch Neutral, Klar, DX und Warm; "
             "'current' verwendet die aktuelle CarenDMR-Einstellung.",
    )
    ap.add_argument("--pause", type=float, default=3.0)
    args = ap.parse_args()

    sound_dir = Path(args.sound_dir)
    files = [sound_dir / f"{i}_AB.mp3" for i in range(1, args.count + 1)]
    missing = [str(path) for path in files if not path.is_file()]
    if missing:
        raise SystemExit("Fehlende Referenzdateien: " + ", ".join(missing))

    timing_initialize(ROOT)
    cfg = BrandMeisterConfigStore(ROOT / "config" / "brandmeister.local.json").load()
    enc_service = EncoderService(ROOT)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    requested_profiles = (
        ("Neutral", "Klar", "DX", "Warm") if args.profile == "all" else (args.profile,)
    )
    root_outdir = ROOT / "logs" / "audio_path_regression" / f"{stamp}_{args.profile}"
    root_outdir.mkdir(parents=True, exist_ok=True)

    all_rows = []
    profile_summaries = []
    total_cases = len(files) * len(requested_profiles)
    ordinal = 0

    print(
        f"CarenDMR Audio-Pfad-Gesamtregression: {total_cases} Sendefälle | "
        f"Profile={', '.join(requested_profiles)} | MP3 ersetzt nur das Mikrofon"
    )

    for profile_label in requested_profiles:
        profile = None if profile_label == "current" else profile_label
        profile_outdir = root_outdir / profile_label
        profile_outdir.mkdir(parents=True, exist_ok=True)
        rows = []
        print(f"\n=== Profil {profile_label} ===", flush=True)

        for index, path in enumerate(files, 1):
            ordinal += 1
            print(f"[{ordinal}/{total_cases}] {profile_label} / {path.name} ...", flush=True)
            try:
                row = _run_case(path, profile, profile_outdir, cfg, enc_service)
                row["requested_profile"] = profile_label
                rows.append(row)
                all_rows.append(row)
                dmr = row["dmr"]
                levels = row["levels"]
                print(
                    f"    Echo {dmr['echo_completeness_percent']:.1f}% | "
                    f"Quelle {levels['reference_source']['rms_dbfs']:.1f} | "
                    f"Gain {levels['after_mic_gain_16k']['rms_dbfs']:.1f} | "
                    f"Profil {levels['after_tx_processing_16k']['rms_dbfs']:.1f} | "
                    f"AMBE {levels['before_ambe_8k']['rms_dbfs']:.1f} | "
                    f"RXdec {levels['rx_after_ambe_8k']['rms_dbfs']:.1f} | "
                    f"RXout {levels['rx_before_soundcard_8k']['rms_dbfs']:.1f} dBFS"
                )
            except Exception as exc:
                row = {
                    "file": path.name,
                    "profile": profile_label,
                    "requested_profile": profile_label,
                    "error": f"{type(exc).__name__}: {exc}",
                }
                rows.append(row)
                all_rows.append(row)
                print(f"    FEHLER: {type(exc).__name__}: {exc}")

            (profile_outdir / "results.json").write_text(
                json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            (root_outdir / "results_all_profiles.json").write_text(
                json.dumps(all_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            if ordinal < total_cases:
                time.sleep(max(0.0, args.pause))

        good = [r for r in rows if "levels" in r]
        if good:
            def avg(path1, path2):
                return sum(float(r[path1][path2]) for r in good) / len(good)
            echo_avg = sum(float(r["dmr"]["echo_completeness_percent"]) for r in good) / len(good)
            complete = sum(float(r["dmr"]["echo_completeness_percent"]) >= 99.0 for r in good)
            clipped = sum(int(r["levels"]["before_ambe_8k"]["clipped_samples"]) for r in good)
            summary = {
                "profile": profile_label,
                "cases_measured": len(good),
                "complete_echo_cases": int(complete),
                "mean_echo_percent": round(echo_avg, 2),
                "mean_reference_rms_dbfs": round(avg("levels", "reference_source") if False else
                    sum(r["levels"]["reference_source"]["rms_dbfs"] for r in good)/len(good), 3),
                "mean_tx_before_ambe_rms_dbfs": round(
                    sum(r["levels"]["before_ambe_8k"]["rms_dbfs"] for r in good)/len(good), 3),
                "mean_rx_after_ambe_rms_dbfs": round(
                    sum(r["levels"]["rx_after_ambe_8k"]["rms_dbfs"] for r in good
                        if r["dmr"]["echo_completeness_percent"] >= 90.0) /
                    max(1, sum(r["dmr"]["echo_completeness_percent"] >= 90.0 for r in good)), 3),
                "mean_rx_before_soundcard_rms_dbfs": round(
                    sum(r["levels"]["rx_before_soundcard_8k"]["rms_dbfs"] for r in good
                        if r["dmr"]["echo_completeness_percent"] >= 90.0) /
                    max(1, sum(r["dmr"]["echo_completeness_percent"] >= 90.0 for r in good)), 3),
                "tx_clipped_samples": int(clipped),
            }
            profile_summaries.append(summary)

    (root_outdir / "profile_comparison.json").write_text(
        json.dumps(profile_summaries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    lines = [
        f"CarenDMR Audio-Profil-Gesamtregression {stamp}",
        f"Profile: {', '.join(requested_profiles)}",
        f"Referenzdateien je Profil: {len(files)}",
        "",
        "Profil | vollständige Echos | Echo Mittel | TX vor AMBE RMS | RX nach AMBE RMS | "
        "RX vor Soundkarte RMS | TX Clipping",
    ]
    for s in profile_summaries:
        lines.append(
            f"{s['profile']} | {s['complete_echo_cases']}/{s['cases_measured']} | "
            f"{s['mean_echo_percent']:.1f}% | "
            f"{s['mean_tx_before_ambe_rms_dbfs']:.2f} dBFS | "
            f"{s['mean_rx_after_ambe_rms_dbfs']:.2f} dBFS | "
            f"{s['mean_rx_before_soundcard_rms_dbfs']:.2f} dBFS | "
            f"{s['tx_clipped_samples']}"
        )
    text = "\n".join(lines) + "\n"
    (root_outdir / "profile_comparison.txt").write_text(text, encoding="utf-8")
    print("\n" + text)
    print("Gesamtergebnis:", root_outdir)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
