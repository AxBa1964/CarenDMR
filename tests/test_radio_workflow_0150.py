from pathlib import Path
from _ui_sources import main_window_source


def test_radio_workflow_short_labels():
    source = main_window_source()
    assert 'self.ptt_button = QPushButton("TX")' in source
    assert 'self.ptt_button.setText("RX")' not in source
    assert 'self.ptt_button.setText("TX")' in source
    assert 'QPushButton("TS1")' in source
    assert 'QPushButton("Privat")' in source


def test_radio_workflow_screenreader_delay_and_silent_seconds():
    source = main_window_source()
    assert "QAccessible.isActive()" not in source
    assert "screenreader_ptt_lead_in_seconds" in source
    # Sekunden stehen nur sichtbar im PTT-Text; es gibt kein eigenes fokussierbares Zählerfeld.
    assert "tx_seconds_label" not in source
    assert 'self.ptt_button.setText(f"TX   {self._tx_elapsed_seconds} s' in source


def test_audio_cue_uses_initialized_audio_send_service():
    from pathlib import Path
    source = main_window_source()
    assert "AudioCuePlayer(self.audio_send_service)" in source
    assert "AudioCuePlayer(self.audio_service)" not in source
