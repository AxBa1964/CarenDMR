from pathlib import Path
import unittest

class TalkgroupOrderSearch02138Tests(unittest.TestCase):
    def test_drop_cancels_qtable_internal_move_and_defers_refresh(self):
        source = Path("carendmr/ui_qt/favorites_widget.py").read_text(encoding="utf-8")
        self.assertIn("event.ignore()", source)
        self.assertIn("QTimer.singleShot(0", source)
        self.assertIn("def _refresh_after_favorite_drop", source)

    def test_exact_numeric_match_ranks_first(self):
        source = Path("carendmr/ui_qt/favorites_widget.py").read_text(encoding="utf-8")
        self.assertIn("if target == query:", source)
        self.assertIn("return (0, 0, channel.target)", source)
        self.assertIn("if query.isdigit() and target.startswith(query):", source)

    def test_favorites_only_have_priority_without_search(self):
        source = Path("carendmr/ui_qt/favorites_widget.py").read_text(encoding="utf-8")
        self.assertIn("if query:", source)
        self.assertIn("Trefferqualität geht bei aktiver Suche vor", source)
        self.assertIn("Ohne Suche bleiben Favoriten wie bisher geschlossen oben", source)
