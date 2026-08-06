from pathlib import Path

from carendmr.version import __version__


def test_radio_workflow_version_and_short_labels():
    assert __version__ == "0.1.9.1.3"
    source = (Path(__file__).parents[1] / "carendmr" / "ui_qt" / "main_window.py").read_text(encoding="utf-8")
    assert 'self.ptt_button = QPushButton("TX")' in source
    assert 'self.ptt_button.setText("RX")' not in source
    assert 'self.ptt_button.setText("TX")' in source
    assert 'QPushButton("TS1")' in source
    assert 'QPushButton("Privat")' in source


def test_radio_workflow_screenreader_delay_and_silent_seconds():
    source = (Path(__file__).parents[1] / "carendmr" / "ui_qt" / "main_window.py").read_text(encoding="utf-8")
    assert "QAccessible.isActive()" not in source
    assert "screenreader_ptt_lead_in_seconds" in source
    assert 'self.tx_seconds_label.setFocusPolicy(Qt.FocusPolicy.NoFocus)' in source
    assert 'self.tx_seconds_label.setAccessibleName("")' in source
    assert 'self.tx_seconds_label.setText(str(self._tx_elapsed_seconds))' in source


def test_audio_cue_uses_initialized_audio_send_service():
    from pathlib import Path
    source = (Path(__file__).parents[1] / "carendmr" / "ui_qt" / "main_window.py").read_text(encoding="utf-8")
    assert "AudioCuePlayer(self.audio_send_service)" in source
    assert "AudioCuePlayer(self.audio_service)" not in source
