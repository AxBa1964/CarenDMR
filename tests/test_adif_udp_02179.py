from datetime import datetime, timezone
import struct

from carendmr.adif_udp import build_adif, build_wsjt_logged_adif_packet


def test_adif_contains_dmr_and_tg_ts():
    text = build_adif(
        callsign="YD1CPJ", station_callsign="DO1DPL",
        qso_at=datetime(2026, 8, 20, 7, 26, tzinfo=timezone.utc),
        talkgroup=91, timeslot=2, name="Adri", country="Indonesia",
    )
    assert "<CALL:6>YD1CPJ" in text
    assert "<BAND:4>70CM" in text
    assert "<MODE:12>DIGITALVOICE" in text
    assert "<SUBMODE:3>DMR" in text
    assert "TG 91 TS2" in text
    assert text.endswith("<EOR>")


def test_wsjt_logged_adif_packet_header():
    packet = build_wsjt_logged_adif_packet("<EOH><EOR>")
    magic, schema, msg_type = struct.unpack(">III", packet[:12])
    assert magic == 0xADBCCBDA
    assert schema == 3
    assert msg_type == 12
