import json
import wave
from pathlib import Path

from carendmr.benchmark.audio_benchmark import AudioBenchmarkService, BenchmarkCase


def _write_wav(path: Path, samples, rate=8000):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        import array
        wav.writeframes(array.array("h", samples).tobytes())


def test_compare_audio_test_uses_codec_loopback_and_persists(tmp_path: Path) -> None:
    service = AudioBenchmarkService(tmp_path)
    try:
        case = BenchmarkCase(
            "DL1ABC", 2620001, 91, 2, 1, "2026-08-06T00:00:00+00:00", 8.0, 64000,
            -12.0, -32.0, -28.0, 20.0, 0.0, 650.0,
            12.0, 80.0, 5.0, 3.0, 0.0, 100.0, 0.0, 10.0, 2.0,
            0, 0, 0, 95, True, ""
        )
        service._append_case(case)
        session = tmp_path / "logs" / "audio_lab" / "AudioTest_1"
        samples = [int(8000 * __import__("math").sin(2 * __import__("math").pi * 700 * i / 8000)) for i in range(8000 * 6)]
        _write_wav(session / "04_codec_loopback_8k.wav", samples)
        (session / "analysis.json").write_text(json.dumps({"files": {}, "extra": {"echo_received": True}}), encoding="utf-8")

        result = service.compare_audio_test(session)

        assert result["reference_name"] == "TG91_Global"
        assert result["reference_stations"] == 1
        assert any(row["key"] == "presence_percent" for row in result["rows"])
        assert (service.reference_dir / "latest_comparison.json").exists()
        assert list((service.reference_dir / "comparisons").glob("modulation_*.json"))
    finally:
        service.close()
