import unittest
from carendmr.brandmeister.config import BrandMeisterConfig
from tools.brandmeister_reference_check import build_reference_config


class BrandMeisterReferenceCheckTests(unittest.TestCase):
    def test_reference_profile_matches_capture(self):
        base = BrandMeisterConfig(
            host="master2.bm262.de", port=62031, dmr_id=2632198,
            password="secret", callsign="DO1DPL"
        )
        cfg = build_reference_config(base)
        self.assertEqual(52.36999, cfg.latitude)
        self.assertEqual("", cfg.description)
        self.assertEqual("www.qrz.com", cfg.url)
        self.assertEqual("20181107_Pi-Star", cfg.software_id)
        self.assertEqual("MMDVM_MMDVM_HS_Hat", cfg.package_id)
        self.assertEqual("secret", cfg.password)


if __name__ == "__main__":
    unittest.main()
