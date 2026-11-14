from pathlib import Path
from _ui_sources import main_window_source


def test_segmented_radio_controls_are_plain_buttons_with_internal_selection():
    source = main_window_source()
    assert 'self.ts1_radio = QPushButton("TS1")' in source
    assert 'self.ts2_radio = QPushButton("TS2")' in source
    assert 'self.group_radio = QPushButton("Gruppe")' in source
    assert 'self.private_radio = QPushButton("Privat")' in source
    assert 'setCheckable(True)' not in source
    assert 'button.setProperty("selected", selected)' in source
    assert source.count('setObjectName("segmentButton")') >= 4


def test_tx_counter_is_shown_in_ptt_button_during_tx():
    """Seit dem Layout-Umbau zeigt der PTT-Knopf selbst die Sendesekunden."""
    source = main_window_source()
    assert "tx_seconds_label" not in source
    assert 'self.ptt_button.setText(f"TX   {self._tx_elapsed_seconds} s' in source


def test_ptt_lead_in_is_configurable_and_persisted():
    preferences = Path("carendmr/application/operating_preferences.py").read_text(encoding="utf-8")
    settings = Path("carendmr/ui_qt/settings_dialog.py").read_text(encoding="utf-8")
    main = main_window_source()
    assert 'screenreader_ptt_lead_in_seconds: float = 1.2' in preferences
    assert 'self.ptt_lead_in_spin.setRange(0.0, 5.0)' in settings
    assert 'self.ptt_lead_in_spin.setSingleStep(0.1)' in settings
    assert 'self.preferences.screenreader_ptt_lead_in_seconds' in main


def test_accessibility_beep_precedes_microphone_start():
    source = main_window_source()
    assert "def _play_tx_ready_beep" in source
    assert "QApplication.beep()" not in source
    assert "self.audio_cues.play_tx_start()" in source
    assert "tx_beep_done" in source
    assert "QTimer.singleShot(120, self._begin_tx)" in source
