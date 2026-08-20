from datetime import datetime, timezone

from carendmr.adif_udp import AdifUdpConfig, build_adif


def test_hrd_default_port_is_2237():
    assert AdifUdpConfig().port == 2237


def test_adif_contains_default_dmr_reports():
    text = build_adif(
        callsign="CN8YOY", station_callsign="DO1DPL",
        qso_at=datetime(2026, 8, 20, 7, 47, 22, tzinfo=timezone.utc),
        talkgroup=91, timeslot=2, name="Younes", country="Morocco",
    )
    assert "<RST_SENT:2>59" in text
    assert "<RST_RCVD:2>59" in text
    assert "<MODE:12>DIGITALVOICE" in text
    assert "<SUBMODE:3>DMR" in text
