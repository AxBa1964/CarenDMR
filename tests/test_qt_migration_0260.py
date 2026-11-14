from pathlib import Path
from unittest.mock import patch

from carendmr import app
from _ui_sources import main_window_source


def test_gui_argument_uses_qt_lazily():
    with patch("carendmr.ui_qt.run_gui", return_value=0) as run_gui:
        assert app.run(["--gui"]) == 0
        run_gui.assert_called_once()


def test_gui_tk_option_was_removed():
    # Die Tkinter-Oberfläche wurde mit 0.2.1.87 entfernt.
    try:
        app.run(["--gui-tk"])
    except SystemExit as exit_:
        assert exit_.code == 2
    else:
        raise AssertionError("--gui-tk darf nicht mehr akzeptiert werden")


def test_qt_source_has_no_own_tts_but_uses_native_accessibility_metadata():
    source = main_window_source()
    assert "CarenAssist" not in source
    assert "setAccessibleName" in source


def test_qt_ptt_remains_stoppable_during_transmit():
    source = main_window_source()
    assert "state in {RadioState.CONNECTED, RadioState.TRANSMITTING}" in source
    assert 'connect_text = "Trennen"' in source
    assert 'self.ptt_button.setText("RX")' not in source
    assert 'self.ptt_button.setProperty("visualState", "tx")' in source


def test_qt_f5_toggles_connection_and_uses_two_tg_fields():
    source = main_window_source()
    assert '"CONNECT": self._toggle_connection' in source
    assert 'self.current_tg_label = QLabel(str(self.preferences.talkgroup))' in source
    assert 'current_caption = QLabel("AKTUELLER KANAL")' in source
    assert 'self.tg_edit = TalkgroupSearchWidget(' in source
    assert 'self.tg_edit.setAccessibleName("Talkgroup")' in source
    assert 'self._apply_pending_talkgroup()' in source
    assert 'QTimer.singleShot(0, self._focus_talkgroup)' in source


def test_qt_timeslot_uses_segment_buttons():
    source = main_window_source()
    assert 'self.ts1_radio = QPushButton("TS1")' in source
    assert 'self.ts2_radio = QPushButton("TS2")' in source
    assert 'return int(text), self._selected_timeslot, self._selected_call_type' in source
    assert 'setCheckable(True)' not in source


def test_qt_rx_state_clears_stale_tx_status():
    source = main_window_source()
    assert 'self.statusBar().showMessage("Empfang aktiv")' in source
    assert 'self.tx_status.setText("RX")' in source


def test_qt_keyboard_priority_for_focused_buttons():
    source = main_window_source()
    assert '"PTT": self._handle_space_shortcut' in source
    # Return/Enter darf nicht als globaler QShortcut gebunden sein. Andernfalls
    # erreicht die Taste die lokale Talkgroup-Suche nicht.
    assert 'for sequence in ("Return", "Enter")' not in source
    assert 'QShortcut(QKeySequence(sequence), self, activated=self._activate_focused_button)' not in source
    assert 'isinstance(widget, QAbstractButton)' in source
    assert 'self.tg_edit.returnPressed.connect' not in source


def test_qt_initial_segment_tab_focus_follows_selected_button():
    source = main_window_source()
    assert "def _sync_radio_controls" in source
    assert "button.setFocusPolicy(Qt.FocusPolicy.NoFocus)" in source
    assert "QWidget.setTabOrder(self.tg_edit, self.connect_button)" in source
    assert "self._sync_radio_controls()" in source


def test_enter_is_local_to_focused_buttons_and_does_not_block_talkgroup_search():
    source = main_window_source()
    assert "QApplication.instance().installEventFilter(self)" in source
    assert "def eventFilter(self, watched, event)" in source
    assert "isinstance(widget, QAbstractButton)" in source
    assert 'QShortcut(QKeySequence("Return")' not in source
    assert 'QShortcut(QKeySequence("Enter")' not in source


def test_message_server_and_known_talkgroup_name_have_separate_places():
    source = main_window_source()
    assert 'QLabel("Message Server: nicht verbunden")' in source
    assert 'self.current_tg_name_label = QLabel("")' in source
    assert "self.tg_edit.textChanged.connect(self._update_known_talkgroup_name)" not in source
    assert "def _set_current_dmr_channel" in source
