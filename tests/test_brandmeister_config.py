import unittest

from carendmr.brandmeister import BrandMeisterConfig


class BrandMeisterConfigTests(unittest.TestCase):
    def make_config(self, **changes):
        values = {
            "host": "master.example.net",
            "port": 62031,
            "dmr_id": 2620000,
            "password": "secret",
            "callsign": "DO1DPL",
        }
        values.update(changes)
        return BrandMeisterConfig(**values)

    def test_productive_defaults_are_brandmeister_compatible(self):
        config = self.make_config()
        config.validate()
        self.assertEqual("20260728_CarenDMR", config.software_id)
        # 0.2.1.90: Diese Kennung nimmt BrandMeister bei direkter Anmeldung an.
        self.assertEqual("MMDVM_MMDVM_HS_Hat", config.package_id)
        self.assertEqual("CarenDMR Digital Voice Client", config.description)

    def test_invalid_software_id_is_rejected(self):
        config = self.make_config(software_id="CarenDMR 0.0.7.6")
        with self.assertRaisesRegex(ValueError, "JJJJMMTT_Name"):
            config.validate()

    def test_package_without_mmdvm_prefix_is_rejected(self):
        config = self.make_config(package_id="CarenDMR_PC")
        with self.assertRaisesRegex(ValueError, "MMDVM"):
            config.validate()


if __name__ == "__main__":
    unittest.main()
