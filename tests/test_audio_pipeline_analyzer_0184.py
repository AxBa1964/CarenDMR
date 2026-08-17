from pathlib import Path
import json

from carendmr.diagnostics import tx_rx_timing


def test_timeline_works_without_global_text_log(tmp_path: Path):
    # Reproduziert den Praxisfehler: keine initialize()-Pflicht für timeline.json.
    tx_rx_timing.start_cycle("PTT EIN")
    session = tmp_path / "AudioTest"
    tx_rx_timing.attach_session(session)
    tx_rx_timing.mark("TX_ERSTES_PCM_FRAME", "Samples=160")
    tx_rx_timing.mark("TX_ERSTES_AMBE_CODEWORT", "Bytes=9")
    payload = json.loads((session / "timeline.json").read_text(encoding="utf-8"))
    steps = [event["step"] for event in payload["events"]]
    assert "START" in steps
    assert "TX_ERSTES_PCM_FRAME" in steps
    assert "TX_ERSTES_AMBE_CODEWORT" in steps
    tx_rx_timing.detach_session()


def test_loopback_metrics_are_named_unambiguously():
    source = (Path(__file__).parents[1] / "carendmr" / "brandmeister" / "live_voice_transmit.py").read_text(encoding="utf-8")
    assert '"codec_loopback_corrected_errors"' in source
    assert '"codec_loopback_decode_exceptions"' in source
    assert '"codec_loopback_frames"' in source
    assert '"codec_loopback_errors"' not in source


def test_loopback_uses_pcmframe_corrected_errors_attribute():
    source = (Path(__file__).parents[1] / "carendmr" / "brandmeister" / "live_voice_transmit.py").read_text(encoding="utf-8")
    assert "decoded_loop.corrected_errors" in source
    assert "decoded_loop.errors" not in source
