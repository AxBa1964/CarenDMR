from pathlib import Path


def test_radio_workflow_short_labels():
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
    # Sekunden stehen nur sichtbar im PTT-Text; es gibt kein eigenes fokussierbares Zählerfeld.
    assert "tx_seconds_label" not in source
    assert 'self.ptt_button.setText(f"TX   {self._tx_elapsed_seconds} s' in source


def test_audio_cue_uses_initialized_audio_send_service():
    from pathlib import Path
    source = (Path(__file__).parents[1] / "carendmr" / "ui_qt" / "main_window.py").read_text(encoding="utf-8")
    assert "AudioCuePlayer(self.audio_send_service)" in source
    assert "AudioCuePlayer(self.audio_service)" not in source
