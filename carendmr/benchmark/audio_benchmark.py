"""Passiver, unterbrechungssicherer DMR-Audio-Benchmark mit Referenz-Engine.

Der Echtzeitpfad liefert nur PCM-Blöcke an eine begrenzte Queue. Analyse,
Aggregation und SQLite-Persistenz laufen ausschließlich im Hintergrundthread.
"""
from __future__ import annotations

import json
import math
import queue
import sqlite3
import statistics
import shutil
import re
import threading
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable


@dataclass(slots=True)
class BenchmarkCase:
    callsign: str
    dmr_id: int
    talkgroup: int
    timeslot: int
    stream_id: int | None
    started_at: str
    duration_seconds: float
    samples: int
    peak_dbfs: float
    rms_dbfs: float
    active_rms_dbfs: float
    crest_factor_db: float
    clipping_percent: float
    spectral_centroid_hz: float
    bass_percent: float
    mid_percent: float
    presence_percent: float
    treble_percent: float
    low_band_percent: float
    speech_band_percent: float
    high_band_percent: float
    silence_percent: float
    level_stability_db: float
    decode_errors: int = 0
    corrected_errors: int = 0
    concealed_bursts: int = 0
    quality_score: int = 0
    accepted: bool = True
    reject_reason: str = ""


@dataclass(slots=True)
class BenchmarkState:
    version: int = 2
    talkgroup: int = 91
    timeslot: int = 2
    status: str = "idle"  # idle, running, paused, stopped, failed
    created_at: str = ""
    updated_at: str = ""
    active_seconds: float = 0.0
    reconnect_attempts: int = 0
    max_reconnect_attempts: int = 5


@dataclass(slots=True)
class _StreamBuffer:
    dmr_id: int
    talkgroup: int
    timeslot: int
    stream_id: int | None
    callsign: str
    started_monotonic: float
    started_at: str
    samples: list[int] = field(default_factory=list)
    decode_errors: int = 0
    corrected_errors: int = 0
    concealed_bursts: int = 0


class AudioBenchmarkService:
    """Sammelt RX-PCM passiv und erzeugt robuste Referenzen pro Rufzeichen."""

    MIN_DURATION_SECONDS = 5.0
    SAMPLE_RATE = 8000
    MIN_REFERENCE_STATIONS = 20

    def __init__(self, project_root: Path, *, contact_lookup: Callable[[int], object | None] | None = None) -> None:
        self.project_root = Path(project_root)
        self.root = self.project_root / "data" / "audio_benchmarks"
        self.root.mkdir(parents=True, exist_ok=True)
        self.references_root = self.root / "references"
        self.references_root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "index.json"
        self.contact_lookup = contact_lookup
        self.reference_name, self.reference_dir = self._ensure_reference_layout()
        self.state_path = self.reference_dir / "current.json"
        self.reference_path = self.reference_dir / "reference.json"
        self.db_path = self.reference_dir / "benchmark.db"
        self.metadata_path = self.reference_dir / "metadata.json"
        self._lock = threading.RLock()
        self._queue: queue.Queue[tuple[str, object]] = queue.Queue(maxsize=512)
        self._stop_worker = threading.Event()
        self._stream: _StreamBuffer | None = None
        self._subscribers: list[Callable[[dict], None]] = []
        self._init_db()
        self._state = self._load_state_and_migrate()
        self._run_started: float | None = None
        self._worker = threading.Thread(target=self._worker_loop, name="CarenDMR-AudioBenchmark", daemon=True)
        self._worker.start()

    @property
    def state(self) -> BenchmarkState:
        with self._lock:
            return BenchmarkState(**asdict(self._state))

    @property
    def is_running(self) -> bool:
        return self._state.status == "running"

    def subscribe(self, callback: Callable[[dict], None]) -> None:
        self._subscribers.append(callback)

    def start(self, talkgroup: int, timeslot: int) -> None:
        import time
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            if not self._state.created_at or self._state.talkgroup != int(talkgroup):
                self._state = BenchmarkState(talkgroup=int(talkgroup), timeslot=int(timeslot), created_at=now, updated_at=now)
            self._state.status = "running"
            self._state.talkgroup = int(talkgroup)
            self._state.timeslot = int(timeslot)
            self._state.updated_at = now
            self._run_started = time.monotonic()
            self._save_locked()
        self._notify()

    def pause(self) -> None:
        self._finish_active_stream()
        self._set_status("paused")

    def stop(self) -> None:
        self._finish_active_stream()
        self._set_status("stopped")

    def resume(self) -> None:
        self.start(self._state.talkgroup, self._state.timeslot)

    def reset(self, talkgroup: int, timeslot: int) -> None:
        with self._lock:
            self._delete_cases_for_target(int(talkgroup), int(timeslot))
            now = datetime.now(timezone.utc).isoformat()
            self._state = BenchmarkState(talkgroup=int(talkgroup), timeslot=int(timeslot), created_at=now, updated_at=now)
            self._run_started = None
            self._stream = None
            self._save_locked()
            self._write_reference_locked()
        self._notify()

    def connection_lost(self) -> bool:
        with self._lock:
            if not self.is_running:
                return False
            self._state.reconnect_attempts += 1
            if self._state.reconnect_attempts >= self._state.max_reconnect_attempts:
                self._state.status = "failed"
                self._state.updated_at = datetime.now(timezone.utc).isoformat()
                self._save_locked()
                self._notify()
                return False
            self._save_locked()
        self._notify()
        return True

    def connection_restored(self) -> None:
        with self._lock:
            self._state.reconnect_attempts = 0
            self._save_locked()
        self._notify()

    def stream_started(self, dmr_id: int, talkgroup: int, timeslot: int, stream_id: int | None) -> None:
        import time
        if not self.is_running or int(talkgroup) != self._state.talkgroup:
            return
        with self._lock:
            current = self._stream
            if current is not None and current.dmr_id == int(dmr_id) and current.talkgroup == int(talkgroup) \
                    and current.timeslot == int(timeslot) and current.stream_id == stream_id:
                return
        self._finish_active_stream()
        callsign = str(dmr_id)
        if self.contact_lookup is not None:
            try:
                contact = self.contact_lookup(int(dmr_id))
                callsign = getattr(contact, "callsign", None) or callsign
            except Exception:
                pass
        with self._lock:
            self._stream = _StreamBuffer(int(dmr_id), int(talkgroup), int(timeslot), stream_id, callsign,
                                         time.monotonic(), datetime.now(timezone.utc).isoformat())

    def add_pcm(self, dmr_id: int, talkgroup: int, timeslot: int, stream_id: int | None,
                samples: Iterable[int], *, corrected_errors: int = 0) -> None:
        if not self.is_running or int(talkgroup) != self._state.talkgroup:
            return
        with self._lock:
            stream = self._stream
            if stream is None or stream.stream_id != stream_id or stream.dmr_id != int(dmr_id):
                self.stream_started(dmr_id, talkgroup, timeslot, stream_id)
                stream = self._stream
            if stream is not None:
                stream.samples.extend(int(v) for v in samples)
                stream.corrected_errors += int(corrected_errors)

    def stream_finished(self, dmr_id: int, talkgroup: int, timeslot: int, stream_id: int | None) -> None:
        with self._lock:
            current = self._stream
            if current is None or current.dmr_id != int(dmr_id) or current.talkgroup != int(talkgroup) \
                    or current.timeslot != int(timeslot) or current.stream_id != stream_id:
                return
        self._finish_active_stream()

    def snapshot(self) -> dict:
        with self._lock:
            cases = self._load_cases(self._state.talkgroup, self._state.timeslot)
            accepted = [c for c in cases if c.accepted]
            station_stats = self._station_aggregates(accepted)
            ref = self._reference(station_stats)
            active_stream = None
            if self._stream is not None:
                active_stream = {"callsign": self._stream.callsign, "dmr_id": self._stream.dmr_id,
                                 "duration_seconds": round(len(self._stream.samples) / self.SAMPLE_RATE, 1),
                                 "stream_id": self._stream.stream_id}
            accepted_seconds = sum(c.duration_seconds for c in accepted)
            maturity = min(100, round(len(station_stats) / self.MIN_REFERENCE_STATIONS * 100))
            return {
                "status": self._state.status, "talkgroup": self._state.talkgroup, "timeslot": self._state.timeslot,
                "active_seconds": round(self._current_active_seconds_locked(), 1), "cases": len(cases),
                "accepted": len(accepted), "rejected": len(cases) - len(accepted),
                "unique_callsigns": len(station_stats), "reconnect_attempts": self._state.reconnect_attempts,
                "active_stream": active_stream, "analysis_queue": self._queue.qsize(), "reference": ref,
                "accepted_speech_seconds": round(accepted_seconds, 1), "reference_maturity": maturity,
                "reference_target": self.MIN_REFERENCE_STATIONS,
                "reference_name": self.reference_name,
            }


    def compare_audio_test(self, session_dir: Path) -> dict:
        """Vergleicht den lokalen AMBE-Loopback mit der aktiven TG-Referenz.

        Als fairer Messpunkt wird ausschließlich ``04_codec_loopback_8k.wav``
        verwendet: sowohl die Benchmark-Signale als auch das eigene Signal sind
        damit bereits durch einen AMBE-Codec gelaufen.
        """
        from carendmr.diagnostics.audio_lab import read_wav

        session_dir = Path(session_dir)
        loopback = session_dir / "04_codec_loopback_8k.wav"
        analysis_path = session_dir / "analysis.json"
        if not loopback.exists():
            raise FileNotFoundError(f"Codec-Loopback fehlt: {loopback}")
        if not analysis_path.exists():
            raise RuntimeError("Der Audio-Test ist noch nicht vollständig ausgewertet.")
        try:
            payload = json.loads(analysis_path.read_text(encoding="utf-8"))
            extra = payload.get("extra") or {}
            if extra.get("echo_received") is False:
                raise RuntimeError("Die Parrot-Rückantwort wurde nicht vollständig empfangen.")
        except json.JSONDecodeError as exc:
            raise RuntimeError("analysis.json ist ungültig.") from exc

        rate, samples = read_wav(loopback)
        if rate != self.SAMPLE_RATE:
            raise RuntimeError(f"Unerwartete Abtastrate im Loopback: {rate} Hz")
        own = self._analyze_reference_pcm(samples)
        with self._lock:
            reference = self._reference(self._station_aggregates([
                case for case in self._load_cases(self._state.talkgroup, self._state.timeslot) if case.accepted
            ]))
        if not reference:
            raise RuntimeError("Für die aktive Referenz liegen noch keine gültigen Stationen vor.")

        metric_specs = (
            ("active_rms_dbfs", "RMS Sprache", "dBFS"),
            ("peak_dbfs", "Peak", "dBFS"),
            ("crest_factor_db", "Crest-Faktor", "dB"),
            ("bass_percent", "Bass 120–300 Hz", "%"),
            ("mid_percent", "Sprachmitten 300–1500 Hz", "%"),
            ("presence_percent", "Präsenz 1500–2500 Hz", "%"),
            ("treble_percent", "Höhen 2500–3400 Hz", "%"),
            ("level_stability_db", "Pegelstabilität", "dB"),
        )
        rows=[]
        for key,label,unit in metric_specs:
            ref=float(reference.get(key,0.0)); mine=float(own.get(key,0.0)); delta=mine-ref
            rows.append({"key":key,"label":label,"unit":unit,"reference":round(ref,3),
                         "own":round(mine,3),"delta":round(delta,3)})

        recommendations=[]
        rms_delta=own["active_rms_dbfs"]-reference.get("active_rms_dbfs",own["active_rms_dbfs"])
        if rms_delta > 2.0: recommendations.append({"parameter":"Mic-Gain","change":-min(15, max(2, round(rms_delta*2))),"reason":"Sprachpegel über Referenz"})
        elif rms_delta < -2.0: recommendations.append({"parameter":"Mic-Gain","change":min(15, max(2, round(-rms_delta*2))),"reason":"Sprachpegel unter Referenz"})
        band_map=(("bass_percent","Tiefen"),("mid_percent","Sprachmitten"),("presence_percent","Präsenz"),("treble_percent","Höhen"))
        for key,param in band_map:
            ref=max(0.1,float(reference.get(key,0.0))); delta=own[key]-ref; relative=delta/ref
            if abs(relative)>=0.18:
                change=-2 if relative>0 else 2
                recommendations.append({"parameter":param,"change":change,"reason":"über Referenz" if relative>0 else "unter Referenz"})
        crest_delta=own["crest_factor_db"]-reference.get("crest_factor_db",own["crest_factor_db"])
        if crest_delta > 3.0: recommendations.append({"parameter":"Dynamik","change":2,"reason":"Pegel schwankt stärker als Referenz"})
        elif crest_delta < -3.0: recommendations.append({"parameter":"Dynamik","change":-2,"reason":"Signal stärker verdichtet als Referenz"})

        result={
            "version":1,"created_at":datetime.now(timezone.utc).isoformat(),
            "reference_name":self.reference_name,"talkgroup":self._state.talkgroup,
            "timeslot":self._state.timeslot,"session_dir":str(session_dir),
            "reference_stations":int(reference.get("stations",0)),
            "reference_qsos":int(reference.get("qsos",0)),
            "rows":rows,"recommendations":recommendations,"own_metrics":own,
        }
        out_dir=self.reference_dir/"comparisons"; out_dir.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
        target=out_dir/f"modulation_{stamp}.json"
        target.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        (self.reference_dir/"latest_comparison.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        return result

    def close(self) -> None:
        if self.is_running:
            self.pause()
        self._stop_worker.set()
        try:
            self._queue.put_nowait(("stop", None))
        except queue.Full:
            pass
        self._worker.join(timeout=2.0)

    def _finish_active_stream(self) -> None:
        with self._lock:
            stream = self._stream
            self._stream = None
        if stream is None:
            return
        duration = len(stream.samples) / self.SAMPLE_RATE
        try:
            self._queue.put_nowait(("analyze", stream))
        except queue.Full:
            self._append_case(self._case_from_stream(stream, duration, accepted=False,
                                                     reject_reason="Analysewarteschlange voll"))

    def _worker_loop(self) -> None:
        while not self._stop_worker.is_set():
            try:
                action, payload = self._queue.get(timeout=0.25)
            except queue.Empty:
                continue
            if action == "stop":
                return
            if action != "analyze":
                continue
            stream = payload
            duration = len(stream.samples) / self.SAMPLE_RATE
            if duration < self.MIN_DURATION_SECONDS:
                case = self._case_from_stream(stream, duration, accepted=False, reject_reason="kürzer als 5 Sekunden")
            else:
                metrics = self._analyze_reference_pcm(stream.samples)
                accepted = metrics["clipping_percent"] <= 0.1 and metrics["active_rms_dbfs"] > -55.0 \
                    and stream.decode_errors == 0
                reason = "" if accepted else "Qualitätsfilter nicht erfüllt"
                score = self._quality_score(metrics, stream)
                case = BenchmarkCase(stream.callsign, stream.dmr_id, stream.talkgroup, stream.timeslot,
                    stream.stream_id, stream.started_at, duration, len(stream.samples),
                    metrics["peak_dbfs"], metrics["rms_dbfs"], metrics["active_rms_dbfs"],
                    metrics["crest_factor_db"], metrics["clipping_percent"], metrics["spectral_centroid_hz"],
                    metrics["bass_percent"], metrics["mid_percent"], metrics["presence_percent"],
                    metrics["treble_percent"], metrics["low_band_percent"], metrics["speech_band_percent"],
                    metrics["high_band_percent"], metrics["silence_percent"], metrics["level_stability_db"],
                    stream.decode_errors, stream.corrected_errors, stream.concealed_bursts, score, accepted, reason)
            self._append_case(case)

    @staticmethod
    def _analyze_reference_pcm(samples: Iterable[int]) -> dict:
        import numpy as np
        x = np.asarray(tuple(samples), dtype=np.float64) / 32768.0
        if x.size == 0:
            return {k: 0.0 for k in ("peak_dbfs", "rms_dbfs", "active_rms_dbfs", "crest_factor_db",
                "clipping_percent", "spectral_centroid_hz", "bass_percent", "mid_percent", "presence_percent",
                "treble_percent", "low_band_percent", "speech_band_percent", "high_band_percent",
                "silence_percent", "level_stability_db")}
        db = lambda v: -120.0 if v <= 1e-12 else 20.0 * math.log10(v)
        abs_x = np.abs(x); peak = float(abs_x.max()); rms = float(np.sqrt(np.mean(x*x)))
        frame_len = 160
        frames = [x[i:i+frame_len] for i in range(0, len(x)-frame_len+1, frame_len)]
        frame_rms = np.asarray([math.sqrt(float(np.mean(f*f))) for f in frames]) if frames else np.asarray([rms])
        threshold = max(10 ** (-50/20), float(np.percentile(frame_rms, 25)) * 1.8)
        active = frame_rms[frame_rms >= threshold]
        active_rms = float(np.sqrt(np.mean(active*active))) if active.size else rms
        silence = float((1.0 - active.size / max(1, frame_rms.size)) * 100.0)
        stability = float(np.std([db(v) for v in active])) if active.size > 1 else 0.0
        window = np.hanning(x.size); power = np.abs(np.fft.rfft(x*window))**2
        freqs = np.fft.rfftfreq(x.size, 1.0/8000); total = float(power.sum())
        def band(lo, hi):
            if total <= 0: return 0.0
            mask = (freqs >= lo) & (freqs < hi)
            return float(power[mask].sum() / total * 100.0)
        centroid = float((freqs*power).sum()/total) if total > 0 else 0.0
        clipping = int(np.count_nonzero(abs_x >= 32760/32768))
        return {"peak_dbfs": db(peak), "rms_dbfs": db(rms), "active_rms_dbfs": db(active_rms),
            "crest_factor_db": max(0.0, db(peak)-db(rms)), "clipping_percent": clipping/len(x)*100.0,
            "spectral_centroid_hz": centroid, "bass_percent": band(120,300), "mid_percent": band(300,1500),
            "presence_percent": band(1500,2500), "treble_percent": band(2500,3400),
            "low_band_percent": band(0,120), "speech_band_percent": band(120,3400),
            "high_band_percent": band(3400,4001), "silence_percent": silence, "level_stability_db": stability}

    @staticmethod
    def _quality_score(metrics: dict, stream: _StreamBuffer) -> int:
        score = 100.0
        score -= min(50.0, metrics["clipping_percent"] * 100.0)
        if metrics["active_rms_dbfs"] < -45: score -= min(25.0, (-45-metrics["active_rms_dbfs"])*1.5)
        if metrics["speech_band_percent"] < 90: score -= min(20.0, (90-metrics["speech_band_percent"])*1.5)
        score -= min(20.0, stream.corrected_errors * 0.2 + stream.decode_errors * 5 + stream.concealed_bursts)
        return max(0, min(100, round(score)))

    def _case_from_stream(self, stream: _StreamBuffer, duration: float, *, accepted: bool, reject_reason: str) -> BenchmarkCase:
        return BenchmarkCase(stream.callsign, stream.dmr_id, stream.talkgroup, stream.timeslot, stream.stream_id,
            stream.started_at, duration, len(stream.samples), -120.0, -120.0, -120.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 100.0, 0.0,
            stream.decode_errors, stream.corrected_errors, stream.concealed_bursts, 0, accepted, reject_reason)

    def _append_case(self, case: BenchmarkCase) -> None:
        with self._lock:
            self._insert_case(case)
            self._state.updated_at = datetime.now(timezone.utc).isoformat()
            self._save_locked(); self._write_reference_locked()
        self._notify()

    def _set_status(self, status: str) -> None:
        import time
        with self._lock:
            if self._run_started is not None:
                self._state.active_seconds += max(0.0, time.monotonic() - self._run_started)
                self._run_started = None
            self._state.status = status; self._state.updated_at = datetime.now(timezone.utc).isoformat(); self._save_locked()
        self._notify()

    def _current_active_seconds_locked(self) -> float:
        import time
        extra = 0.0 if self._run_started is None else max(0.0, time.monotonic() - self._run_started)
        return self._state.active_seconds + extra

    @staticmethod
    def _station_aggregates(cases: list[BenchmarkCase]) -> list[dict]:
        grouped: dict[str, list[BenchmarkCase]] = {}
        for case in cases: grouped.setdefault(case.callsign, []).append(case)
        metric_names = ("peak_dbfs","rms_dbfs","active_rms_dbfs","crest_factor_db","spectral_centroid_hz",
            "bass_percent","mid_percent","presence_percent","treble_percent","low_band_percent",
            "speech_band_percent","high_band_percent","silence_percent","level_stability_db","quality_score")
        result=[]
        for callsign, items in grouped.items():
            row={"callsign":callsign,"qsos":len(items),"speech_seconds":round(sum(i.duration_seconds for i in items),1)}
            for name in metric_names: row[name]=statistics.median(float(getattr(i,name)) for i in items)
            result.append(row)
        return result

    @staticmethod
    def _reference(stations: list[dict]) -> dict:
        if not stations: return {}
        fields_ = ("peak_dbfs","rms_dbfs","active_rms_dbfs","crest_factor_db","spectral_centroid_hz",
            "bass_percent","mid_percent","presence_percent","treble_percent","silence_percent",
            "level_stability_db","quality_score")
        result={"stations":len(stations),"qsos":sum(int(s["qsos"]) for s in stations),
                "speech_seconds":round(sum(float(s["speech_seconds"]) for s in stations),1)}
        for name in fields_:
            values=sorted(float(s[name]) for s in stations)
            result[name]=round(statistics.median(values),3)
            if len(values)>=4:
                q=statistics.quantiles(values,n=4,method="inclusive")
                result[name+"_q25"]=round(q[0],3); result[name+"_q75"]=round(q[2],3)
        return result

    @staticmethod
    def _safe_reference_name(name: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", str(name).strip()).strip("._-")
        return cleaned or "Referenz"

    def _default_reference_name(self, talkgroup: int) -> str:
        return "TG91_Global" if int(talkgroup) == 91 else f"TG{int(talkgroup)}"

    def _ensure_reference_layout(self) -> tuple[str, Path]:
        """Migriert die bisherige Einzelreferenz einmalig in eine benannte Struktur."""
        index = {}
        if self.index_path.exists():
            try:
                index = json.loads(self.index_path.read_text(encoding="utf-8"))
            except Exception:
                index = {}

        active_name = str(index.get("active_reference", "")).strip()
        legacy_state = self.root / "current.json"
        legacy_db = self.root / "benchmark.db"
        legacy_ref = self.root / "reference.json"

        if not active_name:
            talkgroup = 91
            timeslot = 2
            if legacy_state.exists():
                try:
                    state_data = json.loads(legacy_state.read_text(encoding="utf-8"))
                    talkgroup = int(state_data.get("talkgroup", 91))
                    timeslot = int(state_data.get("timeslot", 2))
                except Exception:
                    pass
            active_name = self._default_reference_name(talkgroup)
            active_dir = self.references_root / self._safe_reference_name(active_name)
            active_dir.mkdir(parents=True, exist_ok=True)
            for source in (legacy_state, legacy_db, legacy_ref):
                if source.exists():
                    target = active_dir / source.name
                    if not target.exists():
                        shutil.move(str(source), str(target))
            self._write_metadata_file(active_dir, active_name, talkgroup, timeslot, migrated=True)
            self._write_index(active_name)
            return active_name, active_dir

        active_dir = self.references_root / self._safe_reference_name(active_name)
        active_dir.mkdir(parents=True, exist_ok=True)
        if not (active_dir / "metadata.json").exists():
            self._write_metadata_file(active_dir, active_name, 91, 2, migrated=False)
        return active_name, active_dir

    def _write_index(self, active_name: str) -> None:
        references = []
        for directory in sorted(self.references_root.iterdir()):
            if directory.is_dir():
                references.append(directory.name)
        payload = {"version": 1, "active_reference": active_name, "references": references}
        temp = self.index_path.with_suffix(".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temp.replace(self.index_path)

    @staticmethod
    def _write_metadata_file(directory: Path, name: str, talkgroup: int, timeslot: int, *, migrated: bool) -> None:
        path = directory / "metadata.json"
        if path.exists():
            return
        now = datetime.now(timezone.utc).isoformat()
        payload = {
            "version": 1,
            "name": name,
            "talkgroup": int(talkgroup),
            "timeslot": int(timeslot),
            "description": "Globale Referenz TG91" if int(talkgroup) == 91 else f"Referenz TG{int(talkgroup)}",
            "created_at": now,
            "updated_at": now,
            "migrated_from_legacy": bool(migrated),
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _update_metadata_locked(self) -> None:
        try:
            payload = json.loads(self.metadata_path.read_text(encoding="utf-8")) if self.metadata_path.exists() else {}
        except Exception:
            payload = {}
        ref = self._reference(self._station_aggregates([c for c in self._load_cases(self._state.talkgroup, self._state.timeslot) if c.accepted]))
        payload.update({
            "version": 1,
            "name": self.reference_name,
            "talkgroup": self._state.talkgroup,
            "timeslot": self._state.timeslot,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "stations": int(ref.get("stations", 0)),
            "valid_qsos": int(ref.get("qsos", 0)),
            "speech_seconds": float(ref.get("speech_seconds", 0.0)),
        })
        temp = self.metadata_path.with_suffix(".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temp.replace(self.metadata_path)

    def _init_db(self) -> None:
        cols = ",\n".join(f"{f.name} {self._sqlite_type(f.name)}" for f in fields(BenchmarkCase))
        with sqlite3.connect(self.db_path) as db:
            db.execute(f"CREATE TABLE IF NOT EXISTS cases (id INTEGER PRIMARY KEY AUTOINCREMENT, {cols})")
            db.execute("CREATE INDEX IF NOT EXISTS idx_cases_target ON cases(talkgroup,timeslot)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_cases_callsign ON cases(callsign)")

    @staticmethod
    def _sqlite_type(name: str) -> str:
        if name in {"callsign","started_at","reject_reason"}: return "TEXT"
        if name in {"stream_id"}: return "INTEGER"
        if name in {"accepted"}: return "INTEGER"
        if name in {"dmr_id","talkgroup","timeslot","samples","decode_errors","corrected_errors","concealed_bursts","quality_score"}: return "INTEGER"
        return "REAL"

    def _insert_case(self, case: BenchmarkCase) -> None:
        data=asdict(case); names=list(data); placeholders=",".join("?" for _ in names)
        values=[int(data[n]) if n=="accepted" else data[n] for n in names]
        with sqlite3.connect(self.db_path) as db:
            db.execute(f"INSERT INTO cases ({','.join(names)}) VALUES ({placeholders})", values)

    def _load_cases(self, tg: int, ts: int) -> list[BenchmarkCase]:
        names=[f.name for f in fields(BenchmarkCase)]
        with sqlite3.connect(self.db_path) as db:
            rows=db.execute(f"SELECT {','.join(names)} FROM cases WHERE talkgroup=? AND timeslot=? ORDER BY id",(tg,ts)).fetchall()
        return [BenchmarkCase(**{n:(bool(v) if n=="accepted" else v) for n,v in zip(names,row)}) for row in rows]

    def _delete_cases_for_target(self, tg: int, ts: int) -> None:
        with sqlite3.connect(self.db_path) as db: db.execute("DELETE FROM cases WHERE talkgroup=? AND timeslot=?",(tg,ts))

    def _load_state_and_migrate(self) -> BenchmarkState:
        if not self.state_path.exists(): return BenchmarkState()
        try:
            data=json.loads(self.state_path.read_text(encoding="utf-8"))
            legacy_cases=data.pop("cases",[])
            if legacy_cases:
                existing=self._load_cases(int(data.get("talkgroup",91)),int(data.get("timeslot",2)))
                if not existing:
                    for item in legacy_cases:
                        self._insert_case(self._migrate_legacy_case(item))
            allowed={f.name for f in fields(BenchmarkState)}
            data={k:v for k,v in data.items() if k in allowed}; data["version"]=2
            if data.get("status")=="running": data["status"]="paused"
            return BenchmarkState(**data)
        except Exception:
            return BenchmarkState()

    @staticmethod
    def _migrate_legacy_case(item: dict) -> BenchmarkCase:
        return BenchmarkCase(item.get("callsign",""),int(item.get("dmr_id",0)),int(item.get("talkgroup",91)),
            int(item.get("timeslot",2)),item.get("stream_id"),item.get("started_at",""),float(item.get("duration_seconds",0)),
            int(item.get("samples",0)),float(item.get("peak_dbfs",-120)),float(item.get("rms_dbfs",-120)),
            float(item.get("rms_dbfs",-120)),float(item.get("crest_factor_db",0)),float(item.get("clipping_percent",0)),
            float(item.get("spectral_centroid_hz",0)),0.0,0.0,0.0,0.0,float(item.get("low_band_percent",0)),
            float(item.get("speech_band_percent",0)),float(item.get("high_band_percent",0)),0.0,0.0,
            int(item.get("decode_errors",0)),int(item.get("corrected_errors",0)),int(item.get("concealed_bursts",0)),
            0,bool(item.get("accepted",False)),str(item.get("reject_reason","")))

    def _save_locked(self) -> None:
        temp=self.state_path.with_suffix(".tmp")
        temp.write_text(json.dumps(asdict(self._state),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        temp.replace(self.state_path)

    def _write_reference_locked(self) -> None:
        cases=self._load_cases(self._state.talkgroup,self._state.timeslot)
        ref=self._reference(self._station_aggregates([c for c in cases if c.accepted]))
        payload={"version":2,"talkgroup":self._state.talkgroup,"timeslot":self._state.timeslot,
                 "updated_at":datetime.now(timezone.utc).isoformat(),"reference":ref}
        temp=self.reference_path.with_suffix(".tmp")
        temp.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); temp.replace(self.reference_path)
        self._update_metadata_locked()

    def _notify(self) -> None:
        snapshot=self.snapshot()
        for callback in tuple(self._subscribers):
            try: callback(snapshot)
            except Exception: pass
