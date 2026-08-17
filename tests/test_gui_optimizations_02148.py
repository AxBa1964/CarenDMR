from pathlib import Path
import unittest


class GuiOptimizations02148Tests(unittest.TestCase):
    def test_qrz_button_has_fixed_reserved_slot(self):
        source = Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
        self.assertIn("setRetainSizeWhenHidden(True)", source)
        self.assertIn('self.qrz_button.setObjectName("qrzCompactButton")', source)
        self.assertIn("self.qrz_button.setVisible(False)", source)

    def test_dmr_channel_has_all_favorites_combo(self):
        source = Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
        self.assertIn("self.favorite_combo = QComboBox", source)
        self.assertIn('combo.addItem("Alle Favoriten …", None)', source)
        self.assertIn("for favorite in self.favorite_service.favorites:", source)
        self.assertIn("self._activate_favorite(favorite, source_label=", source)

    def test_combo_and_hot_buttons_share_activation_logic(self):
        source = Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
        self.assertIn("def _activate_favorite(", source)
        self.assertIn('source_label="Schnellwahl"', source)
        self.assertIn('source_label="Favorit"', source)

    def test_current_channel_meta_is_visible(self):
        source = Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
        self.assertIn("self.current_channel_meta_label", source)
        self.assertIn('f"TS{self._selected_timeslot} · {call_text}"', source)

    def test_compact_styles_exist(self):
        source = Path("carendmr/ui_qt/theme.py").read_text(encoding="utf-8")
        self.assertIn("QPushButton#qrzCompactButton", source)
        self.assertIn("QComboBox#favoriteCombo", source)
        self.assertIn("QLabel#compactHint", source)


if __name__ == "__main__":
    unittest.main()
