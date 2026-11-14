from pathlib import Path
from _ui_sources import main_window_source

ROOT = Path(__file__).resolve().parents[1]
MAIN = main_window_source()
CUES = (ROOT / "carendmr" / "ui_qt" / "audio_cue.py").read_text(encoding="utf-8")


def test_ts_and_call_type_have_short_accessibility_names_only():
    assert 'button.setAccessibleDescription("")' in MAIN
    assert 'Umschalten mit F6' not in MAIN
    assert 'Umschalten mit F7' not in MAIN
    assert 'announce=True' in MAIN


def test_accessibility_lead_in_does_not_depend_on_qaccessible_detection():
    assert 'QAccessible.isActive()' not in MAIN
    assert 'screenreader_ptt_lead_in_seconds * 1000' in MAIN


def test_start_and_stop_audio_cues_are_separate():
    assert 'play_tx_start' in CUES
    assert 'play_tx_stop' in CUES
    assert '1_500.0' in CUES
    assert 'tx_stop_beeps_done' in MAIN


def test_start_focus_moves_to_talkgroup():
    assert 'QTimer.singleShot(150, window._focus_talkgroup)' in MAIN
