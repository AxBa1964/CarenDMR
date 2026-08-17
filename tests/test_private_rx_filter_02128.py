from pathlib import Path

def test_private_rx_targets_own_dmr_id():
    source = Path("carendmr/brandmeister/listen.py").read_text(encoding="utf-8")
    assert 'if target_call_type == "private":' in source
    assert "packet.destination_id == config.dmr_id" in source
    assert "packet.destination_id == target_talkgroup" in source

def test_parrot_direction_is_documented_in_filter():
    source = Path("carendmr/brandmeister/listen.py").read_text(encoding="utf-8")
    assert "TX 2632198 -> 9990, RX 9990 -> 2632198" in source
