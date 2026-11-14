import json
from pathlib import Path

from carendmr.audio.tuner import TxAudioTunerSettings
from carendmr.benchmark.audio_benchmark import AudioBenchmarkService


def test_reference_contains_robust_statistics():
    stations = [
        {"callsign": f"T{i}", "qsos": 1, "speech_seconds": 10.0,
         "peak_dbfs": -20+i, "rms_dbfs": -30+i, "active_rms_dbfs": -28+i,
         "crest_factor_db": 8+i, "spectral_centroid_hz": 1000+i,
         "bass_percent": 10+i, "mid_percent": 60-i, "presence_percent": 20+i,
         "treble_percent": 5+i, "silence_percent": 2+i,
         "level_stability_db": 3+i, "quality_score": 80+i}
        for i in range(5)
    ]
    ref = AudioBenchmarkService._reference(stations)
    assert "active_rms_dbfs_mean" in ref
    assert "active_rms_dbfs_stddev" in ref
    assert "active_rms_dbfs_p10" in ref
    assert "active_rms_dbfs_p90" in ref
    assert ref["stations"] == 5


def test_neutral_profile_is_unmodified_except_safety_limiter():
    settings = TxAudioTunerSettings()
    assert settings.profile == "Neutral"
    assert settings.low_db == settings.mids_db == settings.presence_db == settings.high_db == 0.0
    assert settings.dynamics_percent == 0
    assert settings.limiter_percent == 20
