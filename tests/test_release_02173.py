from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")

def test_tx_limit_supports_zero_unlimited():
    text = read("carendmr/application/audio_send_service.py")
    assert "MIN_TX_SAFETY_LIMIT_SECONDS = 0" in text
    assert "86400.0 if self._tx_safety_limit_seconds == 0" in text
    settings = read("carendmr/ui_qt/settings_dialog.py")
    assert "self.tx_limit_spin.setRange(0, 300)" in settings
    assert 'setSpecialValueText("Unbegrenzt")' in settings

def test_tx_warning_last_ten_seconds():
    text = read("carendmr/ui_qt/main_window.py")
    assert "0 < remaining <= 10" in text
    assert 'setProperty("visualState", "warning")' in text
    assert "play_tx_warning" in text
    assert 'pttButton[visualState="warning"]' in read("carendmr/ui_qt/theme.py")

def test_qso_recorder_uses_digital_tx_and_rx():
    text = read("carendmr/ui_qt/main_window.py")
    assert "QsoRecordingService" in text
    assert "set_tx_pcm_observer(self.qso_recording_service.add_tx)" in text
    assert "self.qso_recording_service.add_rx(samples)" in text
    assert "Mitschnitt starten" in text
    service = read("carendmr/application/qso_recording_service.py")
    assert "Mitschnitt_" in service
    assert "SAMPLE_RATE = 8000" in service

def test_recording_stops_on_disconnect_and_target_change():
    text = read("carendmr/ui_qt/main_window.py")
    assert 'Mitschnitt wegen Trennen beendet' in text
    assert 'Mitschnitt wegen Zielwechsel beendet' in text

def test_qso_history_spoken_rows_are_green():
    text = read("carendmr/ui_qt/history_widget.py")
    assert "QColor(220, 242, 220)" in text
    assert "QColor(24, 48, 24)" in text

def test_current_station_can_be_marked_worked():
    text = read("carendmr/ui_qt/main_window.py")
    assert "Als QSO markieren" in text
    assert "Weiteres QSO markieren" in text
    assert "def _mark_current_station_worked" in text
    history = read("carendmr/application/qso_history_service.py")
    assert "def mark_worked" in history
    assert "def last_worked_at" in history

def test_recent_stations_show_last_qso():
    text = read("carendmr/ui_qt/main_window.py")
    assert '["Zeit", "Rufzeichen", "Name", "Land", "Letztes QSO"]' in text

def test_changed_python_syntax():
    files = (
        "carendmr/application/__init__.py",
        "carendmr/application/audio_send_service.py",
        "carendmr/application/parrot_test_service.py",
        "carendmr/application/qso_history_service.py",
        "carendmr/application/qso_recording_service.py",
        "carendmr/ui_qt/audio_cue.py",
        "carendmr/ui_qt/history_widget.py",
        "carendmr/ui_qt/main_window.py",
        "carendmr/ui_qt/settings_dialog.py",
        "carendmr/ui_qt/theme.py",
    )
    for rel in files:
        ast.parse(read(rel))
