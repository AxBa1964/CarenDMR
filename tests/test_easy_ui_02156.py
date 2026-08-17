from pathlib import Path
from threading import Event

from carendmr import app
from carendmr.application.operating_controller import OperatingController
from carendmr.application.radio_state_machine import RadioState


class Store:
    def subscribe(self, listener):
        self.listener = listener


class Receive:
    def __init__(self):
        self.state_store = Store()
        self.is_running = True
        self.wait_timeout = None

    def wait(self, timeout):
        self.wait_timeout = timeout
        self.is_running = False
        return True


class Manager:
    def __init__(self):
        self.kwargs = None
        self.disconnected = False

    def connect(self, tg, ts, call_type):
        return True

    def disconnect(self):
        self.disconnected = True

    def run_parrot_hold_to_talk(self, stop_event, **kwargs):
        self.kwargs = kwargs
        return "ok"


def test_easy_argument_is_available():
    args = app._build_parser().parse_args(["--easy"])
    assert args.easy is True


def test_operating_controller_keeps_tx_callbacks_inside_facade():
    receive = Receive()
    manager = Manager()
    controller = OperatingController(manager, receive)
    controller.radio_state.synchronize(RadioState.CONNECTED)
    callback = lambda: None
    result = controller.ptt(Event(), optimize=True, tx_complete_callback=callback)
    assert result == "ok"
    assert manager.kwargs["optimize"] is True
    assert manager.kwargs["tx_complete_callback"] is callback


def test_operating_controller_can_wait_for_disconnect():
    receive = Receive()
    manager = Manager()
    controller = OperatingController(manager, receive)
    controller.radio_state.synchronize(RadioState.CONNECTED)
    assert controller.disconnect(wait_timeout=8.0) is True
    assert manager.disconnected is True
    assert receive.wait_timeout == 8.0


def test_easy_ui_does_not_import_brandmeister_or_connection_manager_directly_for_actions():
    source = (Path(__file__).parents[1] / "carendmr" / "ui_qt" / "easy_window.py").read_text(encoding="utf-8")
    assert "carendmr.brandmeister" not in source
    assert ".run_parrot_hold_to_talk(" not in source
    assert "self.connection_manager.connect(" not in source
    assert "self.connection_manager.disconnect(" not in source
    assert "self.controller.connect(" in source
    assert "self.controller.disconnect(" in source
    assert "self.controller.ptt(" in source


def test_easy_ui_has_only_three_primary_tab_controls_and_no_station_announcement():
    source = (Path(__file__).parents[1] / "carendmr" / "ui_qt" / "easy_window.py").read_text(encoding="utf-8")
    assert "QWidget.setTabOrder(self.talkgroup_edit, self.connect_button)" in source
    assert "QWidget.setTabOrder(self.connect_button, self.ptt_button)" in source
    assert "current_call" not in source
    assert "Aktuelle Station" not in source


def test_easy_talkgroup_is_prepared_for_digit_by_digit_screenreader_output():
    source = (Path(__file__).parents[1] / "carendmr" / "ui_qt" / "easy_window.py").read_text(encoding="utf-8")
    assert "QLineEdit(self._spaced_digits(self.preferences.talkgroup))" in source
    assert 'replace(" ", "")' in source
    assert "editingFinished.connect(self._format_talkgroup_for_speech)" in source


def test_easy_ptt_accessibility_is_short_and_does_not_overlap_start_cue():
    source = (Path(__file__).parents[1] / "carendmr" / "ui_qt" / "easy_window.py").read_text(encoding="utf-8")
    assert 'self.ptt_button.setAccessibleDescription("")' in source
    assert "Startet oder beendet das Senden" not in source
    assert 'setAccessibleName("PTT, Senden aktiv")' not in source
    assert 'self.ptt_button, "Senden."' in source


def test_easy_buttons_support_enter_explicitly():
    source = (Path(__file__).parents[1] / "carendmr" / "ui_qt" / "easy_window.py").read_text(encoding="utf-8")
    assert "class EasyButton(QPushButton)" in source
    assert "Qt.Key.Key_Return" in source
    assert "Qt.Key.Key_Enter" in source


def test_easy_suppresses_transient_disconnected_announcement_while_connecting():
    source = (Path(__file__).parents[1] / "carendmr" / "ui_qt" / "easy_window.py").read_text(encoding="utf-8")
    assert "self._connect_requested = True" in source
    assert "and not self._connect_requested" in source
