import json
import time
from pathlib import Path

from carendmr.benchmark import AudioBenchmarkService


def test_benchmark_persists_and_resumes(tmp_path: Path):
    service = AudioBenchmarkService(tmp_path)
    service.start(91, 2)
    service.stream_started(1234567, 91, 2, 77)
    # 6 seconds of deterministic speech-like PCM.
    samples = tuple(int(5000 * ((i % 80) / 40.0 - 1.0)) for i in range(6 * 8000))
    service.add_pcm(1234567, 91, 2, 77, samples)
    service.stream_finished(1234567, 91, 2, 77)
    deadline = time.time() + 3
    while time.time() < deadline and service.snapshot()["cases"] == 0:
        time.sleep(0.02)
    snap = service.snapshot()
    assert snap["accepted"] == 1
    assert snap["unique_callsigns"] == 1
    assert snap["reference"]["stations"] == 1
    service.pause()
    service.close()

    restored = AudioBenchmarkService(tmp_path)
    assert restored.snapshot()["accepted"] == 1
    assert restored.state.status == "paused"
    restored.close()


def test_short_stream_is_rejected_without_blocking(tmp_path: Path):
    service = AudioBenchmarkService(tmp_path)
    service.start(262, 2)
    service.stream_started(1, 262, 2, 1)
    service.add_pcm(1, 262, 2, 1, [100] * 8000)
    service.stream_finished(1, 262, 2, 1)
    deadline = time.time() + 3
    while time.time() < deadline and service.snapshot()["cases"] == 0:
        time.sleep(0.02)
    assert service.snapshot()["rejected"] == 1
    service.close()


def test_reconnect_stops_after_five_attempts(tmp_path: Path):
    service = AudioBenchmarkService(tmp_path)
    service.start(91, 2)
    assert [service.connection_lost() for _ in range(5)] == [True, True, True, True, False]
    assert service.state.status == "failed"
    service.close()


def test_repeated_activity_events_do_not_split_one_qso(tmp_path: Path):
    service = AudioBenchmarkService(tmp_path)
    service.start(91, 2)
    samples = [500] * 480
    for _ in range(100):
        service.stream_started(4040495, 91, 2, 1234)
        service.add_pcm(4040495, 91, 2, 1234, samples)
    snap = service.snapshot()
    assert snap["cases"] == 0
    assert snap["active_stream"]["dmr_id"] == 4040495
    assert snap["active_stream"]["duration_seconds"] == 6.0
    service.stream_finished(4040495, 91, 2, 1234)
    deadline = time.time() + 3
    while time.time() < deadline and service.snapshot()["cases"] == 0:
        time.sleep(0.02)
    snap = service.snapshot()
    assert snap["accepted"] == 1
    assert snap["rejected"] == 0
    service.close()


def test_finish_for_foreign_stream_is_ignored(tmp_path: Path):
    service = AudioBenchmarkService(tmp_path)
    service.start(91, 2)
    service.stream_started(111, 91, 2, 10)
    service.add_pcm(111, 91, 2, 10, [300] * 8000)
    service.stream_finished(222, 91, 2, 99)
    assert service.snapshot()["active_stream"]["dmr_id"] == 111
    service.close()


def test_reference_engine_migrates_legacy_json_and_writes_sqlite(tmp_path: Path):
    root = tmp_path / "data" / "audio_benchmarks"
    root.mkdir(parents=True)
    legacy = {
        "version": 1, "talkgroup": 91, "timeslot": 2, "status": "paused",
        "created_at": "2026-08-06T00:00:00+00:00", "updated_at": "2026-08-06T00:00:00+00:00",
        "active_seconds": 10.0, "reconnect_attempts": 0, "max_reconnect_attempts": 5,
        "cases": [{
            "callsign": "TEST1", "dmr_id": 1, "talkgroup": 91, "timeslot": 2, "stream_id": 7,
            "started_at": "2026-08-06T00:00:00+00:00", "duration_seconds": 8.0, "samples": 64000,
            "peak_dbfs": -10.0, "rms_dbfs": -28.0, "crest_factor_db": 18.0, "clipping_percent": 0.0,
            "spectral_centroid_hz": 600.0, "low_band_percent": 1.0, "speech_band_percent": 98.0,
            "high_band_percent": 1.0, "decode_errors": 0, "corrected_errors": 0,
            "concealed_bursts": 0, "accepted": True, "reject_reason": ""
        }]
    }
    (root / "current.json").write_text(json.dumps(legacy), encoding="utf-8")
    service = AudioBenchmarkService(tmp_path)
    snap = service.snapshot()
    assert snap["accepted"] == 1
    assert snap["unique_callsigns"] == 1
    assert (root / "references" / "TG91_Global" / "benchmark.db").exists()
    assert service.state.version == 2
    service.close()


def test_reference_engine_exposes_tuner_metrics(tmp_path: Path):
    service = AudioBenchmarkService(tmp_path)
    service.start(91, 2)
    service.stream_started(123, 91, 2, 1)
    samples = [int(6000 * __import__('math').sin(2 * __import__('math').pi * 700 * i / 8000)) for i in range(6 * 8000)]
    service.add_pcm(123, 91, 2, 1, samples)
    service.stream_finished(123, 91, 2, 1)
    deadline = time.time() + 3
    while time.time() < deadline and service.snapshot()["cases"] == 0:
        time.sleep(0.02)
    ref = service.snapshot()["reference"]
    for key in ("active_rms_dbfs", "bass_percent", "mid_percent", "presence_percent", "treble_percent", "quality_score"):
        assert key in ref
    assert (tmp_path / "data" / "audio_benchmarks" / "references" / "TG91_Global" / "reference.json").exists()
    service.close()


def test_named_reference_migrates_existing_tg91_data_once(tmp_path: Path):
    root = tmp_path / "data" / "audio_benchmarks"
    root.mkdir(parents=True)
    state = {
        "version": 2, "talkgroup": 91, "timeslot": 2, "status": "paused",
        "created_at": "2026-08-06T00:00:00+00:00", "updated_at": "2026-08-06T00:00:00+00:00",
        "active_seconds": 3600.0, "reconnect_attempts": 0, "max_reconnect_attempts": 5,
    }
    (root / "current.json").write_text(json.dumps(state), encoding="utf-8")
    # Legacy database is created by an initial service and moved back to simulate 0.2.0.
    legacy = AudioBenchmarkService(tmp_path)
    legacy.close()
    named = root / "references" / "TG91_Global"
    for filename in ("current.json", "benchmark.db", "reference.json"):
        source = named / filename
        if source.exists():
            source.replace(root / filename)
    (root / "index.json").unlink(missing_ok=True)
    try:
        named.rmdir()
    except OSError:
        pass

    service = AudioBenchmarkService(tmp_path)
    snap = service.snapshot()
    assert snap["reference_name"] == "TG91_Global"
    target = root / "references" / "TG91_Global"
    assert (target / "benchmark.db").exists()
    assert (target / "current.json").exists()
    assert (target / "metadata.json").exists()
    index = json.loads((root / "index.json").read_text(encoding="utf-8"))
    assert index["active_reference"] == "TG91_Global"
    service.close()


def test_named_reference_metadata_tracks_statistics(tmp_path: Path):
    service = AudioBenchmarkService(tmp_path)
    service.start(91, 2)
    service.stream_started(1234567, 91, 2, 77)
    samples = tuple(int(5000 * ((i % 80) / 40.0 - 1.0)) for i in range(6 * 8000))
    service.add_pcm(1234567, 91, 2, 77, samples)
    service.stream_finished(1234567, 91, 2, 77)
    deadline = time.time() + 3
    while time.time() < deadline and service.snapshot()["cases"] == 0:
        time.sleep(0.02)
    metadata_path = tmp_path / "data" / "audio_benchmarks" / "references" / "TG91_Global" / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["name"] == "TG91_Global"
    assert metadata["stations"] == 1
    assert metadata["valid_qsos"] == 1
    service.close()
