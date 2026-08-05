from pathlib import Path


def test_segmented_radio_controls_are_plain_buttons_with_internal_selection():
    source = Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
    assert 'self.ts1_radio = QPushButton("TS1")' in source
    assert 'self.ts2_radio = QPushButton("TS2")' in source
    assert 'self.group_radio = QPushButton("Gruppe")' in source
    assert 'self.private_radio = QPushButton("Privat")' in source
    assert 'setCheckable(True)' not in source
    assert 'button.setProperty("selected", selected)' in source
    assert source.count('setObjectName("segmentButton")') >= 4


def test_tx_counter_reserves_space_and_only_contains_a_value_during_tx():
    source = Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
    assert 'self.tx_seconds_label.setFixedHeight(34)' in source
    assert 'self.tx_seconds_label.setVisible(True)' in source
    assert 'self.tx_seconds_label.setText("0")' in source
    assert 'self.tx_seconds_label.clear()' in source


def test_ptt_lead_in_is_configurable_and_persisted():
    preferences = Path("carendmr/application/operating_preferences.py").read_text(encoding="utf-8")
    settings = Path("carendmr/ui_qt/settings_dialog.py").read_text(encoding="utf-8")
    main = Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
    assert 'screenreader_ptt_lead_in_seconds: float = 1.2' in preferences
    assert 'self.ptt_lead_in_spin.setRange(0.0, 5.0)' in settings
    assert 'self.ptt_lead_in_spin.setSingleStep(0.1)' in settings
    assert 'self.preferences.screenreader_ptt_lead_in_seconds' in main


def test_accessibility_beep_precedes_microphone_start():
    source = Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
    assert "def _play_tx_ready_beep" in source
    assert "QApplication.beep()" not in source
    assert "self.audio_cues.play_tx_start()" in source
    assert "tx_beep_done" in source
    assert "QTimer.singleShot(120, self._begin_tx)" in source
