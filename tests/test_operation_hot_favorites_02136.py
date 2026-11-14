from pathlib import Path
import unittest
from _ui_sources import main_window_source

class OperationHotFavorites02136Tests(unittest.TestCase):
    def test_three_hot_buttons_use_first_three_favorites(self):
        source = main_window_source()
        self.assertIn("for index in range(3):", source)
        self.assertIn('self.favorite_combo = QComboBox', source)
        self.assertIn("favorites = self.favorite_service.favorites[:3]", source)

    def test_connected_hot_button_disconnects_then_reconnects(self):
        source = main_window_source()
        self.assertIn("self._pending_hot_favorite = channel", source)
        self.assertIn("self._disconnect()", source)
        self.assertIn("if self._pending_hot_favorite is not None:", source)
        self.assertIn("self._connect_hot_favorite(selected)", source)
        self.assertIn("self._connect()", source)

    def test_hot_favorite_applies_complete_channel(self):
        source = main_window_source()
        self.assertIn("channel = favorite.to_dmr_channel()", source)
        self.assertIn("self._set_current_dmr_channel(normalized)", source)
        self.assertIn("self._save_preferences()", source)

    def test_recent_table_refreshes_after_history_insert(self):
        main = main_window_source()
        history = Path("carendmr/application/qso_history_service.py").read_text(encoding="utf-8")
        self.assertIn("def subscribe_added", history)
        self.assertIn("callback(entry)", history)
        self.assertIn('self._updates.put(("history_added", entry))', main)
        self.assertIn('elif kind == "history_added":', main)
        self.assertIn("self._refresh_recent_stations(force=True)", main)

    def test_tx_uses_nearly_full_card_width(self):
        source = main_window_source()
        self.assertIn("control_layout.setContentsMargins(2, 10, 2, 10)", source)
        self.assertIn("self.ptt_button.setMinimumHeight(150)", source)
