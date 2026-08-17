from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / 'carendmr/ui_qt/main_window.py').read_text(encoding='utf-8')
THEME = (ROOT / 'carendmr/ui_qt/theme.py').read_text(encoding='utf-8')


def test_radio_flags_use_f6_f7_for_keyboard_and_mouse_clicks_remain():
    assert 'button.setProperty("radioFlag", True)' in MAIN
    assert 'not button.property("radioFlag")' in MAIN
    assert 'if button.property("radioFlag")' in MAIN
    assert 'self.ts1_radio.clicked.connect' in MAIN
    assert 'self.group_radio.clicked.connect' in MAIN


def test_tx_counter_stops_immediately_when_rx_is_requested():
    stop_block = MAIN[MAIN.index('def _stop_tx'):MAIN.index('def _finish_tx')]
    assert 'self._tx_elapsed_timer.stop()' in stop_block
    assert 'self.tx_seconds_label.clear()' in stop_block
    assert 'self.ptt_button.setText("TX")' in stop_block


def test_custom_tone_replaces_qapplication_beep():
    tone_block = MAIN[MAIN.index('def _play_tx_ready_beep'):MAIN.index('def _begin_tx')]
    assert 'QApplication.beep()' not in tone_block
    assert 'self.audio_cues.play_tx_start()' in tone_block
    cue = (ROOT / 'carendmr/ui_qt/audio_cue.py').read_text(encoding='utf-8')
    assert 'manager.backend.play_samples' in cue
    assert 'tx_beep_done' in MAIN


def test_segment_buttons_are_compact():
    assert 'button.setFixedSize(48, 28)' in MAIN
    assert 'button.setFixedSize(68, 28)' in MAIN
    assert 'font-size: 11px' in THEME
