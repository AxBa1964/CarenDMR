from pathlib import Path
import unittest
from _ui_sources import main_window_source

class TunerCoachUi02133Tests(unittest.TestCase):
    def test_tuner_has_no_duplicate_assistant_buttons_or_status_line(self):
        source = main_window_source()
        self.assertNotIn('QPushButton("Parrot vorbereiten")', source)
        self.assertNotIn('QPushButton("Audio-Assistent")', source)
        self.assertNotIn('self.audio_tuner_status = QLabel', source)

    def test_tuner_is_separate_window(self):
        source = main_window_source()
        self.assertIn('self.audio_tuner_button = QPushButton("Audio-Tuner…")', source)
        self.assertIn('dialog.setWindowTitle("DMR Audio-Tuner")', source)
        self.assertNotIn('self.audio_tuner_panel = QWidget', source)

    def test_coach_recommendation_uses_target_value(self):
        source = Path("carendmr/ui_qt/audio_coach_widget.py").read_text(encoding="utf-8")
        self.assertIn("def _recommendation_target", source)
        self.assertIn("Nächster empfohlener Schritt:", source)
        self.assertIn("weitere Änderung", source)
