from pathlib import Path
import json
from carendmr.diagnostics import tx_rx_timing


def test_timeline_is_written_into_audio_session(tmp_path: Path):
    tx_rx_timing.initialize(tmp_path)
    tx_rx_timing.start_cycle("PTT Test")
    path = tx_rx_timing.attach_session(tmp_path / "logs" / "audio_lab" / "AudioTest_x")
    tx_rx_timing.mark("TX_ERSTES_PCM", "Samples=160")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["events"][-1]["step"] == "TX_ERSTES_PCM"
    assert payload["events"][-1]["elapsed_ms"] >= 0
    tx_rx_timing.detach_session()
