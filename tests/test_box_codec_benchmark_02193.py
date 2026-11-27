"""0.2.1.93: Codec-Messung und Linux-Build für CarenDMR.box."""
from __future__ import annotations

import wave
from pathlib import Path

import pytest

from carendmr.app import _build_parser
from carendmr.box import codec_benchmark as cb

ROOT = Path(__file__).resolve().parents[1]


class FakeCodec:
    def __init__(self) -> None:
        self.encoded = 0
        self.decoded = 0

    def encode_2450x1150(self, pcm: tuple[int, ...]) -> bytes:
        assert len(pcm) == cb.FRAME_SAMPLES
        self.encoded += 1
        return bytes(9)

    def decode_2450x1150(self, ambe: bytes) -> tuple[int, ...]:
        assert len(ambe) == 9
        self.decoded += 1
        return (0,) * cb.FRAME_SAMPLES


class StepClock:
    """Jeder Aufruf rückt die Zeit vor: Kodieren 2 ms, Dekodieren 1 ms."""

    def __init__(self) -> None:
        self.now = 0.0
        self.calls = 0

    def __call__(self) -> float:
        step = (0.0, 0.002, 0.001)[self.calls % 3]
        self.calls += 1
        self.now += step
        return self.now


def test_percentile_interpolates():
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert cb._percentile(values, 50.0) == 3.0
    assert cb._percentile(values, 100.0) == 5.0
    assert cb._percentile([7.0], 99.0) == 7.0
    assert cb._percentile([0.0, 10.0], 95.0) == pytest.approx(9.5)


def test_timing_stats_rejects_empty():
    with pytest.raises(ValueError):
        cb.TimingStats.from_samples([])


def test_synthetic_frames_are_reproducible_and_valid():
    first = cb.synthetic_speech_frames(5)
    assert first == cb.synthetic_speech_frames(5)
    assert len(first) == 5
    for frame in first:
        assert len(frame) == cb.FRAME_SAMPLES
        assert all(-32768 <= value <= 32767 for value in frame)
    assert any(value != 0 for value in first[0])


def test_run_benchmark_measures_encode_and_decode_separately():
    codec = FakeCodec()
    frames = cb.synthetic_speech_frames(20)
    result = cb.run_benchmark(
        codec, frames, warmup_frames=3, clock=StepClock(), temperature=lambda: 50.0
    )
    assert codec.encoded == 23 and codec.decoded == 23
    assert result.encode.count == 20
    assert result.encode.mean_ms == pytest.approx(2.0)
    assert result.decode.mean_ms == pytest.approx(1.0)
    assert result.combined_p99_ms == pytest.approx(3.0)
    assert result.share_of_frame == pytest.approx(0.15)
    assert result.verdict == "gut"
    assert result.cpu_temp_start_c == 50.0


def _result(encode_ms: float, decode_ms: float) -> cb.BenchmarkResult:
    return cb.BenchmarkResult(
        encode=cb.TimingStats.from_samples([encode_ms]),
        decode=cb.TimingStats.from_samples([decode_ms]),
        cpu_temp_start_c=None,
        cpu_temp_end_c=None,
    )


def test_verdict_thresholds():
    assert _result(2.5, 2.5).verdict == "gut"  # 25 %
    assert _result(5.0, 5.0).verdict == "knapp"  # 50 %
    assert _result(8.0, 4.0).verdict == "zu langsam"  # 60 %


def test_report_is_german_and_complete():
    text = cb.format_report(_result(1.0, 0.5), device="Raspberry Pi 4 Model B (aarch64)", source="Test")
    for expected in ("Kodieren", "Dekodieren", "Raspberry Pi 4", "Bewertung    : gut", "CPU-Temperatur: Start unbekannt"):
        assert expected in text


def test_wav_frames_reads_8khz_mono(tmp_path):
    path = tmp_path / "probe.wav"
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        handle.writeframes(b"\x01\x00" * 400)
    frames = cb.wav_frames(path)
    assert len(frames) == 2
    assert frames[0][0] == 1


def test_wav_frames_rejects_wrong_format(tmp_path):
    path = tmp_path / "probe.wav"
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(48000)
        handle.writeframes(b"\x00\x00" * 800)
    with pytest.raises(ValueError, match="8000 Hz"):
        cb.wav_frames(path)


def test_cpu_temperature(tmp_path):
    sensor = tmp_path / "temp"
    sensor.write_text("48312\n", encoding="ascii")
    assert cb.cpu_temperature_c(sensor) == pytest.approx(48.312)
    assert cb.cpu_temperature_c(tmp_path / "fehlt") is None


def test_cli_reports_missing_bridge(tmp_path, capsys, monkeypatch):
    from carendmr import app_paths

    monkeypatch.setattr(app_paths, "native_dir", lambda _root: tmp_path / "native")
    assert cb.run_codec_benchmark_cli(tmp_path) == 2
    output = capsys.readouterr().out
    assert "build_md380_dynarmic_linux.sh" in output


def test_parser_knows_codec_benchmark_options():
    args = _build_parser().parse_args(["--codec-benchmark", "--frames", "500", "--setup-codec"])
    assert args.codec_benchmark and args.frames == 500 and args.setup_codec


def test_benchmark_module_is_qt_free():
    text = (ROOT / "carendmr" / "box" / "codec_benchmark.py").read_text(encoding="utf-8")
    assert "PySide6" not in text and "numpy" not in text


def test_linux_build_script():
    text = (ROOT / "native" / "build_md380_dynarmic_linux.sh").read_text(encoding="utf-8")
    assert 'COMMIT="55c9a2c6d502567380c7dfaf4a2e3cc4dd6d1dd5"' in text
    assert "aarch64|x86_64" in text
    assert "libboost-dev" in text
    assert 'cmake -S "$CMAKE_PROJECT" -B "$BUILD_DIR" -G Ninja' in text
    assert "grep -q carendmr_md380_init_files" in text
    # Keine Firmware im Build (seit 0.2.1.89).
    assert "xxd" not in text and "md380.org" not in text
