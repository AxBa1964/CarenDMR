from __future__ import annotations

import json
from pathlib import Path
import wave

from carendmr.benchmark.modulation_test import ModulationTestTracker


def _wav(path: Path, frames: int = 160) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        handle.writeframes(b"\0\0" * frames)


def test_tracker_waits_for_complete_parrot_and_writes_manifest(tmp_path: Path) -> None:
    root = tmp_path / "audio_lab"
    root.mkdir()
    tracker = ModulationTestTracker(root)
    tracker.arm()

    session = root / "AudioTest_20260806_120000_000"
    session.mkdir()
    _wav(session / "04_codec_loopback_8k.wav")
    (session / "analysis.json").write_text(
        json.dumps({"extra": {"echo_received": True}}), encoding="utf-8"
    )
    _wav(session / "rx_20260806_120001_000_03_parrot_nach_ambe_8k.wav")

    first = tracker.poll()
    assert first.state in {"capturing_parrot", "finalizing"}
    second = tracker.poll()
    assert not second.ready_for_comparison
    third = tracker.poll()
    assert third.ready_for_comparison
    manifest = json.loads((session / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["state"] == "completed"
    assert manifest["ready_for_comparison"] is True


def test_tracker_reports_missing_echo_as_failure(tmp_path: Path) -> None:
    root = tmp_path / "audio_lab"
    root.mkdir()
    tracker = ModulationTestTracker(root)
    tracker.arm()
    session = root / "AudioTest_20260806_120000_001"
    session.mkdir()
    _wav(session / "04_codec_loopback_8k.wav")
    (session / "analysis.json").write_text(
        json.dumps({"extra": {"echo_received": False}}), encoding="utf-8"
    )
    result = tracker.poll()
    assert result.failed
    assert "Parrot" in result.message
