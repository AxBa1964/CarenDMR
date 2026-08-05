from pathlib import Path
from unittest.mock import patch

from carendmr import app
from carendmr.version import __version__


def test_version_is_qt_migration_0265():
    assert __version__ == "0.1.6.8"


def test_gui_argument_uses_qt_lazily():
    with patch("carendmr.ui_qt.run_gui", return_value=0) as run_gui:
        assert app.run(["--gui"]) == 0
        run_gui.assert_called_once()


def test_gui_tk_remains_available():
    with patch("carendmr.ui.run_gui", return_value=0) as run_gui:
        assert app.run(["--gui-tk"]) == 0
        run_gui.assert_called_once()


def test_qt_source_has_no_own_tts_but_uses_native_accessibility_metadata():
    source = (Path(__file__).parents[1] / "carendmr" / "ui_qt" / "main_window.py").read_text(encoding="utf-8")
    assert "CarenAssist" not in source
    assert "setAccessibleName" in source


def test_qt_ptt_remains_stoppable_during_transmit():
    source = (Path(__file__).parents[1] / "carendmr" / "ui_qt" / "main_window.py").read_text(encoding="utf-8")
    assert "state in {RadioState.CONNECTED, RadioState.TRANSMITTING}" in source
    assert 'connect_text = "Trennen"' in source
    assert 'self.ptt_button.setText("RX")' not in source
    assert 'self.ptt_button.setProperty("visualState", "tx")' in source


def test_qt_f5_toggles_connection_and_uses_two_tg_fields():
    source = (Path(__file__).parents[1] / "carendmr" / "ui_qt" / "main_window.py").read_text(encoding="utf-8")
    assert '"CONNECT": self._toggle_connection' in source
    assert 'self.current_tg_label = QLabel(str(self.preferences.talkgroup))' in source
    assert 'current_caption = QLabel("Aktuelle TG")' in source
    assert 'target_layout.addWidget(QLabel("Neue Talkgroup")' in source
    assert 'self.tg_edit = QLineEdit()' in source
    assert 'self._apply_pending_talkgroup()' in source
    assert 'QTimer.singleShot(0, self._focus_talkgroup)' in source


def test_qt_timeslot_uses_segment_buttons():
    source = (Path(__file__).parents[1] / "carendmr" / "ui_qt" / "main_window.py").read_text(encoding="utf-8")
    assert 'self.ts1_radio = QPushButton("TS1")' in source
    assert 'self.ts2_radio = QPushButton("TS2")' in source
    assert 'return int(text), self._selected_timeslot, self._selected_call_type' in source
    assert 'setCheckable(True)' not in source


def test_qt_rx_state_clears_stale_tx_status():
    source = (Path(__file__).parents[1] / "carendmr" / "ui_qt" / "main_window.py").read_text(encoding="utf-8")
    assert 'self.statusBar().showMessage("Empfang aktiv")' in source
    assert 'self.tx_status.setText("RX")' in source


def test_qt_keyboard_priority_for_focused_buttons():
    source = (Path(__file__).parents[1] / "carendmr" / "ui_qt" / "main_window.py").read_text(encoding="utf-8")
    assert '"PTT": self._handle_space_shortcut' in source
    assert 'for sequence in ("Return", "Enter")' in source
    assert 'activated=self._activate_focused_button' in source
    assert 'isinstance(widget, QAbstractButton)' in source
    assert 'self.tg_edit.returnPressed.connect' not in source


def test_qt_initial_segment_tab_focus_follows_selected_button():
    source = (Path(__file__).parents[1] / "carendmr" / "ui_qt" / "main_window.py").read_text(encoding="utf-8")
    assert "def _sync_radio_controls" in source
    assert "button.setFocusPolicy(Qt.FocusPolicy.NoFocus)" in source
    assert "QWidget.setTabOrder(self.tg_edit, self.connect_button)" in source
    assert "self._sync_radio_controls()" in source
