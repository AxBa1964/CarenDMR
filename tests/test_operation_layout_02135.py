from pathlib import Path
import unittest
from _ui_sources import main_window_source

class OperationLayout02135Tests(unittest.TestCase):
    def test_redundant_target_removed_from_station_and_recent_table(self):
        source = main_window_source()
        station = source[source.index("detail_positions = ("):source.index("recent_heading = QLabel")]
        self.assertNotIn('("Ziel", self.target_label', station)
        self.assertIn('QTableWidget(0, 5, station_card)', source)
        self.assertIn('["Zeit", "Rufzeichen", "Name", "Land", "Letztes QSO"]', source)

    def test_tx_is_dominant_control(self):
        source = main_window_source()
        self.assertIn("self.ptt_button.setMinimumHeight(150)", source)
        self.assertIn("self.ptt_button.setMaximumHeight(150)", source)
