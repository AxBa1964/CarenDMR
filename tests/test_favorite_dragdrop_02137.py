from pathlib import Path
import unittest

class FavoriteDragDrop02137Tests(unittest.TestCase):
    def test_only_favorites_are_draggable_and_order_is_persisted(self):
        source = Path("carendmr/ui_qt/favorites_widget.py").read_text(encoding="utf-8")
        self.assertIn("class FavoriteOrderTable(QTableWidget)", source)
        self.assertIn("self._owner.service.move(old_index, destination_row)", source)
        self.assertIn("item.setFlags(item.flags() | Qt.ItemFlag.ItemIsDragEnabled)", source)
        self.assertIn("item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsDragEnabled)", source)

    def test_favorites_stay_sorted_before_nonfavorites(self):
        source = Path("carendmr/ui_qt/favorites_widget.py").read_text(encoding="utf-8")
        self.assertIn("0 if favorite_for(c) is not None else 1", source)
        self.assertIn("favorite_for(c).position if favorite_for(c) is not None else 999999", source)

    def test_tx_is_visibly_taller_downwards(self):
        source = Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
        self.assertIn("self.ptt_button.setMinimumHeight(150)", source)
        self.assertIn("self.ptt_button.setMaximumHeight(150)", source)
        self.assertIn('self.ptt_button.setText(f"TX   {self._tx_elapsed_seconds} s")', source)
        self.assertNotIn("tx_seconds_label", source)
