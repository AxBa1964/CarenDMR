"""Tests für die reproduzierbaren RPTC-Profile des Diagnosewerkzeugs."""

import unittest

from carendmr.brandmeister import BrandMeisterConfig
from tools.brandmeister_check import build_reference_config, build_test_config


class BrandMeisterCheckProfileTests(unittest.TestCase):
    def setUp(self):
        self.local = BrandMeisterConfig(
            host="example.org",
            port=62031,
            dmr_id=2632198,
            password="secret",
            callsign="DO1DPL",
            latitude=1.0,
            longitude=2.0,
            location="LOCAL",
            description="CarenDMR",
            frequency_hz=123456789,
            url="",
            software_id="CarenDMR 0.0.7.5",
            package_id="CarenDMR",
        )

    def test_reference_profile_contains_captured_values(self):
        result = build_reference_config(self.local)
        self.assertEqual("20181107_Pi-Star", result.software_id)
        self.assertEqual("MMDVM_MMDVM_HS_Hat", result.package_id)
        self.assertEqual("www.qrz.com", result.url)
        self.assertEqual("", result.description)
        self.assertEqual(438_800_000, result.frequency_hz)

    def test_single_software_change_keeps_other_reference_values(self):
        result, changed = build_test_config(
            self.local, profile="reference", software=True
        )
        self.assertEqual("CarenDMR 0.0.7.5", result.software_id)
        self.assertEqual("MMDVM_MMDVM_HS_Hat", result.package_id)
        self.assertEqual("www.qrz.com", result.url)
        self.assertEqual(["Software-ID"], changed)

    def test_free_software_value_replaces_only_software_id(self):
        result, changed = build_test_config(
            self.local,
            profile="reference",
            software_value="20260728_CarenDMR",
        )
        self.assertEqual("20260728_CarenDMR", result.software_id)
        self.assertEqual("MMDVM_MMDVM_HS_Hat", result.package_id)
        self.assertEqual(["Software-ID = '20260728_CarenDMR'"], changed)

    def test_free_package_value_replaces_only_package_id(self):
        result, changed = build_test_config(
            self.local,
            profile="reference",
            package_value="CarenDMR_CarenDMR_HS_Hat",
        )
        self.assertEqual("20181107_Pi-Star", result.software_id)
        self.assertEqual("CarenDMR_CarenDMR_HS_Hat", result.package_id)
        self.assertEqual(["Package-ID = 'CarenDMR_CarenDMR_HS_Hat'"], changed)

    def test_local_profile_is_unchanged(self):
        result, changed = build_test_config(self.local, profile="local")
        self.assertIs(self.local, result)
        self.assertEqual(["vollständiges lokales CarenDMR-Profil"], changed)


if __name__ == "__main__":
    unittest.main()
