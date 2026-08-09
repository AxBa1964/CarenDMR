from pathlib import Path
import unittest

class OperationLayout02135Tests(unittest.TestCase):
    def test_redundant_target_removed_from_station_and_recent_table(self):
        source = Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
        station = source[source.index("detail_positions = ("):source.index("recent_heading = QLabel")]
        self.assertNotIn('("Ziel", self.target_label', station)
        self.assertIn('QTableWidget(0, 4, station_card)', source)
        self.assertIn('["Zeit", "Rufzeichen", "Name", "Land"]', source)

    def test_tx_is_dominant_control(self):
        source = Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
        self.assertIn("self.ptt_button.setMinimumHeight(150)", source)
        self.assertIn("self.ptt_button.setMaximumHeight(150)", source)
