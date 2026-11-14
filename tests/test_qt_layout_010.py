from pathlib import Path
from _ui_sources import main_window_source


def test_layout_v1_keeps_existing_controls_and_dark_theme():
    source = main_window_source()
    for token in (
        'self.tg_edit = TalkgroupSearchWidget(',
        'self.ts1_radio = QPushButton("TS1")',
        'self.ts2_radio = QPushButton("TS2")',
        'self.group_radio = QPushButton("Gruppe")',
        'self.private_radio = QPushButton("Privat")',
        'self.connect_button = QPushButton("Verbinden")',
        'self.ptt_button = QPushButton("TX")',
        'def _restore_tab_order',
    ):
        assert token in source


def test_layout_uses_central_theme():
    root = Path(__file__).parents[1]
    source = main_window_source()
    theme = (root / 'carendmr' / 'ui_qt' / 'theme.py').read_text(encoding='utf-8')
    assert 'from carendmr.ui_qt.theme import apply_theme' in source
    assert 'QFrame#headerCard, QFrame#card' in theme
