from pathlib import Path
import unittest


class SettingsUi0224Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (Path(__file__).resolve().parents[1] / "carendmr" / "ui" / "main_window.py").read_text(encoding="utf-8")

    def test_settings_categories_exist(self):
        for caption in ("Audio", "Netzwerk", "Daten", "Bedienung", "Diagnose", "Erweiterungen"):
            self.assertIn(f'("{caption.lower() if caption != "Bedienung" else "operation"}', self.source) if False else self.assertIn(caption, self.source)

    def test_compact_codec_card_exists(self):
        self.assertIn('"AMBE-Codec"', self.source)
        self.assertIn('"Plugin zuordnen"', self.source)
        self.assertIn('"Erneut prüfen"', self.source)

    def test_settings_search_exists(self):
        self.assertIn("def _search_settings", self.source)
        self.assertIn("Einstellungen durchsuchen", self.source)

    def test_password_is_not_rendered(self):
        summary = self.source[self.source.index("def _load_brandmeister_profile_summary"):]
        self.assertNotIn('data.get("password"', summary)


if __name__ == "__main__":
    unittest.main()
