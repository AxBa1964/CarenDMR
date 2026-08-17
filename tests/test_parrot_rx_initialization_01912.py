from pathlib import Path


def _source() -> str:
    return (Path(__file__).parents[1] / "carendmr" / "brandmeister" / "live_voice_transmit.py").read_text(encoding="utf-8")


def test_parrot_rx_is_initialized_before_first_tx_stream() -> None:
    source = _source()
    assert 'timing_mark("RX_INITIALISIERUNG_START")' in source
    assert 'timing_mark("RX_INITIALISIERUNG_BEREIT")' in source
    assert source.index('timing_mark("RX_INITIALISIERUNG_BEREIT")') < source.index("timing_mark('TX_LOGIN_START')")


def test_parrot_rx_state_is_reset_before_echo_wait() -> None:
    source = _source()
    reset = source.index('timing_mark("PARROT_RX_RESET_START")')
    ready = source.index('timing_mark("PARROT_RX_BEREIT")')
    wait = source.index('timing_mark("PARROT_ECHO_WARTE_START")')
    assert reset < ready < wait
    reset_block = source[reset:wait]
    assert "decoder = decoder_factory()" in reset_block
    assert "jitter.reset()" in reset_block
    assert "pending_rx_frames.clear()" in reset_block
    assert "echo_stream_id = None" in reset_block


def test_first_voice_packet_can_initialize_stream_without_header() -> None:
    source = _source()
    assert "if echo_stream_id != packet.stream_id:" in source
    assert 'f"Stream={packet.stream_id:08X};Header=0"' in source
    assert "jitter.reset(first_voice_sequence=packet.sequence)" in source
