import hashlib
import unittest

from carendmr.brandmeister.protocol import (
    build_auth_packet,
    build_close_packet,
    build_config_packet,
    build_login_packet,
    build_ping_packet,
    extract_challenge,
    is_master_ack,
    is_master_nak,
    is_master_pong,
)


class BrandMeisterProtocolTests(unittest.TestCase):
    def test_login_packet(self):
        self.assertEqual(
            b"RPTL\x00\x01\x02\x03",
            build_login_packet(0x00010203),
        )

    def test_auth_packet_uses_sha256_challenge_plus_password(self):
        challenge = bytes.fromhex("11223344")
        expected = (
            b"RPTK"
            + bytes.fromhex("00010203")
            + hashlib.sha256(challenge + b"secret").digest()
        )
        self.assertEqual(
            expected,
            build_auth_packet(0x00010203, challenge, "secret"),
        )
        self.assertEqual(40, len(expected))

    def test_configuration_packet_has_exact_droidstar_length(self):
        packet = build_config_packet(
            dmr_id=2620000,
            callsign="DO1DPL",
            frequency_hz=0,
            latitude=52.0,
            longitude=10.0,
            location="Braunschweig",
            description="CarenDMR",
            url="",
            software_id="CarenDMR 0.0.7",
            package_id="CarenDMR",
        )
        self.assertEqual(302, len(packet))
        self.assertEqual(b"RPTC", packet[:4])
        self.assertEqual(2620000 .to_bytes(4, "big"), packet[4:8])
        self.assertEqual(b"DO1DPL  ", packet[8:16])


    def test_configuration_coordinates_match_droidstar_byte_for_byte(self):
        packet = build_config_packet(
            dmr_id=2632198,
            callsign="DO1DPL",
            frequency_hz=438800000,
            latitude=52.310,
            longitude=10.47,
            location="JO52FI",
            description="CarenDMR",
            url="",
            software_id="CarenDMR 0.0.7.1",
            package_id="CarenDMR",
        )
        self.assertEqual(b"52.31000", packet[38:46])
        self.assertEqual(b"10.470000", packet[46:55])

    def test_ping_and_close(self):
        dmr_id = 2620000
        suffix = dmr_id.to_bytes(4, "big")
        self.assertEqual(b"RPTPING" + suffix, build_ping_packet(dmr_id))
        self.assertEqual(b"RPTCL" + suffix, build_close_packet(dmr_id))

    def test_response_detection(self):
        dmr_id = 2620000
        suffix = dmr_id.to_bytes(4, "big")
        ack = b"RPTACK" + bytes.fromhex("01020304")
        self.assertTrue(is_master_ack(ack))
        self.assertEqual(bytes.fromhex("01020304"), extract_challenge(ack))
        self.assertTrue(is_master_nak(b"MSTNAK"))
        self.assertTrue(is_master_pong(b"MSTPONG" + suffix, dmr_id))
        self.assertFalse(is_master_pong(b"MSTPONG" + b"xxxx", dmr_id))


if __name__ == "__main__":
    unittest.main()
