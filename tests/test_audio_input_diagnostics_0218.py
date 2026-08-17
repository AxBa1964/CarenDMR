from pathlib import Path

from carendmr.benchmark.modulation_test import ModulationTestTracker


def test_abort_writes_aborted_manifest(tmp_path: Path) -> None:
    session = tmp_path / "AudioTest_1"
    session.mkdir()
    tracker = ModulationTestTracker(tmp_path)
    tracker.session_dir = session

    snapshot = tracker.abort("Test abgebrochen: kein Signal.")

    assert snapshot.state == "aborted"
    assert snapshot.failed is True
    payload = (session / "manifest.json").read_text(encoding="utf-8")
    assert '"state": "aborted"' in payload
    assert '"ready_for_comparison": false' in payload


def test_audio_backend_collects_callback_diagnostics() -> None:
    source = Path("carendmr/audio/backend.py").read_text(encoding="utf-8")
    assert '"callbacks": 0' in source
    assert '"native_samples": 0' in source
    assert '"channel_peak"' in source
    assert '"channel_rms"' in source
    assert '"active_channel"' in source


def test_audio_test_persists_input_diagnostics() -> None:
    source = Path("carendmr/application/audio_send_service.py").read_text(encoding="utf-8")
    assert 'input_diagnostics.json' in source
    assert 'AUDIO_INPUT_DIAGNOSE' in source
    assert 'Callbacks=' in source
