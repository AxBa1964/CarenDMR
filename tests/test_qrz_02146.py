import json
import tempfile
import unittest
from pathlib import Path

from carendmr.qrz.service import QrzConfig, QrzNotFound, parse_callsign_profile
from _ui_sources import main_window_source


SAMPLE_XML = b"""<?xml version="1.0"?>
<QRZDatabase version="1.34" xmlns="http://www.qrz.com">
  <Callsign>
    <call>K6KRI</call>
    <fname>TEST</fname>
    <name>OPERATOR</name>
    <addr2>SAN DIEGO</addr2>
    <state>CA</state>
    <country>United States</country>
    <lat>32.7157</lat>
    <lon>-117.1611</lon>
    <grid>DM12</grid>
    <image>https://files.qrz.com/k/k6kri/test.jpg</image>
    <url>https://www.qrz.com/db/K6KRI</url>
    <cqzone>3</cqzone>
    <ituzone>6</ituzone>
  </Callsign>
  <Session><Key>abc123</Key></Session>
</QRZDatabase>"""

NOT_FOUND_XML = b"""<?xml version="1.0"?>
<QRZDatabase xmlns="http://www.qrz.com">
  <Session><Error>Callsign not found</Error></Session>
</QRZDatabase>"""


class Qrz02146Tests(unittest.TestCase):
    def test_profile_parser_reads_qrz_fields(self):
        profile = parse_callsign_profile(SAMPLE_XML)
        self.assertEqual("K6KRI", profile.callsign)
        self.assertEqual("TEST OPERATOR", profile.display_name)
        self.assertEqual("SAN DIEGO", profile.city)
        self.assertEqual("CA", profile.state)
        self.assertEqual("United States", profile.country)
        self.assertEqual("DM12", profile.grid)
        self.assertAlmostEqual(32.7157, profile.latitude)
        self.assertAlmostEqual(-117.1611, profile.longitude)
        self.assertTrue(profile.image_url.endswith("test.jpg"))

    def test_not_found_is_distinguished(self):
        with self.assertRaises(QrzNotFound):
            parse_callsign_profile(NOT_FOUND_XML)

    def test_local_config_loads_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "qrz.local.json"
            path.write_text(json.dumps({
                "username": "DO1DPL",
                "password": "secret",
                "own_callsign": "DO1DPL",
            }), encoding="utf-8")
            config = QrzConfig.load(path)
            self.assertEqual("DO1DPL", config.username)
            self.assertEqual("secret", config.password)
            self.assertEqual("DO1DPL", config.own_callsign)

    def test_local_credentials_are_git_ignored(self):
        source = Path(".gitignore").read_text(encoding="utf-8")
        self.assertIn("*.local.json", source)

    def test_main_window_only_shows_qrz_button_after_found_profile(self):
        source = main_window_source()
        self.assertIn('self.qrz_button = QPushButton("QRZ.com", station_card)', source)
        self.assertIn("setRetainSizeWhenHidden(True)", source)
        self.assertIn("self.qrz_button.setVisible(profile is not None)", source)
        self.assertIn("self._request_qrz_lookup(callsign)", source)

    def test_qrz_window_has_profile_map_and_actions(self):
        source = Path("carendmr/ui_qt/qrz_window.py").read_text(encoding="utf-8")
        self.assertIn('QPushButton("Details")', source)
        self.assertIn('QPushButton("QRZ.com öffnen")', source)
        self.assertIn("QWebEngineView", source)
        self.assertIn("HAM Grid", source)
        self.assertIn("profile.image_url", source)
        self.assertIn("def _detail_view", source)


if __name__ == "__main__":
    unittest.main()
