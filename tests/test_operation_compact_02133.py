from pathlib import Path
import unittest
from _ui_sources import main_window_source

class OperationCompact02134Tests(unittest.TestCase):
    def test_audio_tuner_is_separate_dialog(self):
        source = main_window_source()
        self.assertIn('self.audio_tuner_button = QPushButton("Audio-Tuner…")', source)
        self.assertIn("def _build_audio_tuner_dialog", source)
        self.assertIn('dialog.setWindowTitle("DMR Audio-Tuner")', source)
        operation = source[source.index("def _build_ui"):source.index("def _apply_theme")]
        self.assertNotIn('self.audio_tuner_panel = QWidget', operation)

    def test_recent_three_stations_are_a_real_table(self):
        source = main_window_source()
        self.assertIn('QLabel("ZULETZT GEHÖRT")', source)
        self.assertIn("self.recent_station_table = QTableWidget(0, 5, station_card)", source)
        self.assertIn('["Zeit", "Rufzeichen", "Name", "Land", "Letztes QSO"]', source)
        self.assertIn("self.receive_service.history.list_recent(limit=20)", source)
        self.assertIn("if len(unique) == 3:", source)

    def test_value_fields_have_visual_hierarchy(self):
        source = main_window_source()
        theme = Path("carendmr/ui_qt/theme.py").read_text(encoding="utf-8")
        self.assertIn('value.setObjectName("fieldValue"', source)
        self.assertIn("QLabel#fieldValue", theme)
        self.assertIn("QLabel#tunerValue", theme)

    def test_redundant_large_app_header_is_removed(self):
        source = main_window_source()
        operation = source[source.index("def _build_ui"):source.index("content = QGridLayout()")]
        self.assertNotIn('title = QLabel("CarenDMR")', operation)
        self.assertNotIn('subtitle = QLabel("Funkgerät auf dem Desktop")', operation)

    def test_old_oversized_geometry_is_migrated_once(self):
        source = main_window_source()
        self.assertIn('layout_version = int(payload.get("layout_version", 1)', source)
        self.assertIn('"layout_version": 2', source)
        self.assertIn("self.resize(980, 720)", source)
