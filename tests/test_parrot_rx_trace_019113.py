from pathlib import Path


def _source() -> str:
    return (Path(__file__).parents[1] / "carendmr" / "brandmeister" / "live_voice_transmit.py").read_text(encoding="utf-8")


def test_rx_trace_logs_parsed_packet_before_filtering() -> None:
    source = _source()
    assert 'timing_mark(\n                        "RX_TRACE_DMRD"' in source
    assert source.index('"RX_TRACE_DMRD"') < source.index("reject_reasons = []")


def test_rx_trace_logs_rejection_decode_and_summary() -> None:
    source = _source()
    for marker in (
        "RX_TRACE_PARSE_FEHLER",
        "RX_TRACE_VERWORFEN",
        "RX_TRACE_KEIN_VOICE",
        "RX_TRACE_DECODE_FEHLER",
        "RX_TRACE_DECODE_OK",
        "RX_TRACE_SUMME",
    ):
        assert marker in source


def test_rx_trace_is_bounded() -> None:
    source = _source()
    assert "rx_trace_limit = 24" in source
    assert "rx_trace_packets <= rx_trace_limit" in source
