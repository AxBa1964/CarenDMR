from pathlib import Path

import pytest

from carendmr.domain import DmrChannel


def test_dmr_channel_normalizes_text_fields_and_call_type() -> None:
    channel = DmrChannel(262, 2, " GROUP ", " Deutschland ", " Deutschland ", " national ").normalized()
    assert channel.target == 262
    assert channel.timeslot == 2
    assert channel.call_type == "group"
    assert channel.name == "Deutschland"
    assert channel.country == "Deutschland"
    assert channel.description == "national"
    assert channel.target_label == "Talkgroup"


def test_private_channel_uses_dmr_id_label() -> None:
    channel = DmrChannel(2632198, 2, "private", "Heidi").normalized()
    assert channel.target_label == "DMR-ID"
    assert not channel.is_group_call


@pytest.mark.parametrize(
    "channel",
    [
        DmrChannel(0, 2, "group"),
        DmrChannel(91, 3, "group"),
        DmrChannel(91, 2, "unknown"),
    ],
)
def test_invalid_dmr_channels_are_rejected(channel: DmrChannel) -> None:
    with pytest.raises(ValueError):
        channel.normalized()


def test_operation_page_uses_dmr_channel_wording() -> None:
    source = Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
    assert 'QLabel("DMR-KANAL")' in source
    assert 'QLabel("Talkgroup")' in source
    assert 'setPlaceholderText("Talkgroup nach Nummer oder Name suchen")' in source
    assert 'setAccessibleName("Talkgroup")' in source
    assert 'QLabel("FUNKZIEL")' not in source
