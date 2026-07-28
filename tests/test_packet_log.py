import io
import unittest

from carendmr.network import PacketLogger, identify_ascii_packet


class PacketLoggerTests(unittest.TestCase):
    def test_disabled_logger_writes_nothing(self):
        stream = io.StringIO()
        logger = PacketLogger(enabled=False, stream=stream)

        logger.log("TX", "BrandMeister", "RPTL", b"RPTL\x00\x00\x00\x01")

        self.assertEqual("", stream.getvalue())

    def test_logger_contains_direction_length_hex_and_ascii(self):
        stream = io.StringIO()
        logger = PacketLogger(
            enabled=True,
            stream=stream,
            include_timestamp=False,
        )

        logger.log("TX", "BrandMeister", "RPTL", b"RPTL\x00\x00\x00\x01")
        output = stream.getvalue()

        self.assertIn("[TX] BrandMeister RPTL (8 Bytes)", output)
        self.assertIn("52 50 54 4C 00 00 00 01", output)
        self.assertIn("RPTL....", output)

    def test_packet_identification(self):
        self.assertEqual("RPTACK", identify_ascii_packet(b"RPTACK\x01\x02"))
        self.assertEqual("MSTNAK", identify_ascii_packet(b"MSTNAK"))
        self.assertEqual("DMRD", identify_ascii_packet(b"DMRDdata"))
        self.assertEqual("UNKNOWN", identify_ascii_packet(b"other"))

    def test_invalid_direction_is_rejected(self):
        logger = PacketLogger(enabled=True, stream=io.StringIO())
        with self.assertRaises(ValueError):
            logger.log("OUT", "BrandMeister", "RPTL", b"RPTL")


if __name__ == "__main__":
    unittest.main()
