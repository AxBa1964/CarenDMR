import unittest

from carendmr.vocoder import PcmFrame


class PcmFrameTests(unittest.TestCase):
    def test_requires_exactly_160_samples(self):
        with self.assertRaisesRegex(ValueError, "160"):
            PcmFrame((0,) * 159, corrected_errors=0)

    def test_rejects_values_outside_signed_16_bit_range(self):
        with self.assertRaisesRegex(ValueError, "16-Bit"):
            PcmFrame((0,) * 159 + (32768,), corrected_errors=0)

    def test_rejects_negative_error_count(self):
        with self.assertRaisesRegex(ValueError, "negativ"):
            PcmFrame((0,) * 160, corrected_errors=-1)


if __name__ == "__main__":
    unittest.main()
