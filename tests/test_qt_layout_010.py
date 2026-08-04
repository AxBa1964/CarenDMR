from pathlib import Path


def test_layout_v1_keeps_existing_controls_and_dark_theme():
    source = (Path(__file__).parents[1] / "carendmr" / "ui_qt" / "main_window.py").read_text(encoding="utf-8")
    for token in (
        'self.tg_edit = QLineEdit()',
        'self.ts1_radio = QRadioButton("TS 1")',
        'self.ts2_radio = QRadioButton("TS 2")',
        'self.group_radio = QRadioButton("Gruppe")',
        'self.private_radio = QRadioButton("Privat")',
        'self.connect_button = QPushButton("Verbinden")',
        'self.ptt_button = QPushButton("PTT – Senden einschalten")',
        'def _restore_tab_order',
    ):
        assert token in source


def test_version_is_010():
    from carendmr.version import __version__
    assert __version__ == "0.1.2.1"


def test_layout_uses_central_theme():
    root = Path(__file__).parents[1]
    source = (root / 'carendmr' / 'ui_qt' / 'main_window.py').read_text(encoding='utf-8')
    theme = (root / 'carendmr' / 'ui_qt' / 'theme.py').read_text(encoding='utf-8')
    assert 'from carendmr.ui_qt.theme import apply_theme' in source
    assert 'QFrame#headerCard, QFrame#card' in theme
