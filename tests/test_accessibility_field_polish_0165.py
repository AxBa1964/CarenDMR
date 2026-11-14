from pathlib import Path
from _ui_sources import main_window_source

ROOT = Path(__file__).resolve().parents[1]
MAIN = main_window_source()


def test_radio_flag_descriptions_are_short_and_not_duplicated():
    assert 'button.setAccessibleDescription("")' in MAIN
    assert 'Umschalten mit F6' not in MAIN
    assert 'Umschalten mit F7' not in MAIN


def test_connection_button_always_has_explicit_accessible_name():
    assert 'self.connect_button.setAccessibleName(connect_text)' in MAIN
    assert 'connect_text = "Verbinden"' in MAIN
    assert 'connect_text = "Trennen"' in MAIN


def test_tx_ready_tone_uses_central_audio_cue_player():
    cue = (ROOT / 'carendmr' / 'ui_qt' / 'audio_cue.py').read_text(encoding='utf-8')
    assert 'play_tx_start' in cue
    assert '1_500.0' in cue
    assert 'np.concatenate' in cue


def test_operation_page_does_not_announce_as_named_group():
    assert 'operation_page.setAccessibleName("")' in MAIN
    assert 'operation_page.setAccessibleDescription("")' in MAIN
