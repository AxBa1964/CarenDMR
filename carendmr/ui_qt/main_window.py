"""Funktionaler Qt-Betrieb für CarenDMR 0.0.26.0.

Diese Stufe portiert ausschließlich den stabilen Funkbetrieb. Es gibt bewusst
keine eigene TTS- oder Screenreader-Sonderlogik.
"""
from __future__ import annotations

import queue
import sys
from pathlib import Path
from threading import Event, Thread

from PySide6.QtCore import QRegularExpression, QTimer, Qt
from PySide6.QtGui import QCloseEvent, QKeySequence, QRegularExpressionValidator, QShortcut
from PySide6.QtWidgets import (
    QApplication, QAbstractButton, QButtonGroup, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QRadioButton,
    QStatusBar, QVBoxLayout, QWidget,
)

from carendmr.application import (
    AudioSendService, ConnectionManager, EncoderService, EventService,
    ParrotTestService, RadioState, RadioStateMachine, ReceiveService,
)
from carendmr.application.operating_preferences import OperatingPreferences, OperatingPreferencesStore
from carendmr.domain import ApplicationState, ConnectionState
from carendmr.version import __version__


class MainWindow(QMainWindow):
    def __init__(self, project_root: Path) -> None:
        super().__init__()
        self.project_root = Path(project_root)
        self.setWindowTitle(f"CarenDMR {__version__} – Qt-Migration")
        self.resize(920, 650)

        self.events = EventService()
        self.preferences_store = OperatingPreferencesStore(self.project_root / "config" / "operating.local.json")
        self.preferences = self.preferences_store.load()
        self.receive_service = ReceiveService(self.project_root, events=self.events)
        self.encoder_service = EncoderService(self.project_root)
        self.audio_send_service = AudioSendService(
            self.project_root,
            mute_receive=self.receive_service.mute_audio_output,
            unmute_receive=self.receive_service.unmute_audio_output,
        )
        self.parrot_service = ParrotTestService(
            self.project_root,
            audio_service=self.audio_send_service,
            encoder_service=self.encoder_service,
        )
        self.connection_manager = ConnectionManager(
            self.receive_service, self.parrot_service, events=self.events
        )
        self.radio_state = RadioStateMachine()
        self._updates: queue.SimpleQueue[tuple[str, object]] = queue.SimpleQueue()
        self._tx_stop_event: Event | None = None
        self._tx_active = False
        self._encoder_ready = False

        self._build_ui()
        self._bind_shortcuts()
        self.receive_service.state_store.subscribe(lambda state: self._updates.put(("state", state)))
        self.events.subscribe(lambda event: self._updates.put(("event", event)))

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._process_updates)
        self._timer.start(100)
        QTimer.singleShot(0, self._verify_encoder)
        self._apply_state(self.receive_service.state_store.get())

    def _build_ui(self) -> None:
        central = QWidget(self)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        target_box = QGroupBox("Funkziel")
        target_form = QFormLayout(target_box)
        self.current_tg_label = QLabel(str(self.preferences.talkgroup))
        self.current_tg_label.setObjectName("currentTalkgroup")
        self.tg_edit = QLineEdit()
        self.tg_edit.setPlaceholderText("Neue Talkgroup")
        self.tg_edit.setMaxLength(8)
        self.tg_edit.setValidator(QRegularExpressionValidator(QRegularExpression(r"[0-9]{0,8}"), self.tg_edit))
        ts_row = QWidget()
        ts_layout = QHBoxLayout(ts_row)
        ts_layout.setContentsMargins(0, 0, 0, 0)
        self.ts1_radio = QRadioButton("Timeslot 1")
        self.ts2_radio = QRadioButton("Timeslot 2")
        self.ts_group = QButtonGroup(self)
        self.ts_group.addButton(self.ts1_radio, 1)
        self.ts_group.addButton(self.ts2_radio, 2)
        (self.ts1_radio if self.preferences.timeslot == 1 else self.ts2_radio).setChecked(True)
        ts_layout.addWidget(self.ts1_radio)
        ts_layout.addWidget(self.ts2_radio)
        ts_layout.addStretch(1)
        call_row = QWidget()
        call_layout = QHBoxLayout(call_row)
        call_layout.setContentsMargins(0, 0, 0, 0)
        self.group_radio = QRadioButton("Gruppenruf")
        self.private_radio = QRadioButton("Privatruf")
        self.call_group = QButtonGroup(self)
        self.call_group.addButton(self.group_radio)
        self.call_group.addButton(self.private_radio)
        (self.private_radio if self.preferences.call_type == "private" else self.group_radio).setChecked(True)
        self.ts1_radio.toggled.connect(self._sync_radio_tab_focus)
        self.ts2_radio.toggled.connect(self._sync_radio_tab_focus)
        self.group_radio.toggled.connect(self._sync_radio_tab_focus)
        self.private_radio.toggled.connect(self._sync_radio_tab_focus)
        self._sync_radio_tab_focus()
        call_layout.addWidget(self.group_radio)
        call_layout.addWidget(self.private_radio)
        call_layout.addStretch(1)
        target_form.addRow("Aktuelle Talkgroup:", self.current_tg_label)
        target_form.addRow("Neue Talkgroup:", self.tg_edit)
        target_form.addRow("Timeslot:", ts_row)
        target_form.addRow("Rufart:", call_row)
        root.addWidget(target_box)

        connection_box = QGroupBox("Verbindung")
        connection_layout = QVBoxLayout(connection_box)
        self.connection_label = QLabel("Getrennt")
        self.server_label = QLabel("Server: Nicht verbunden")
        self.connect_button = QPushButton("Verbinden")
        self.connect_button.clicked.connect(self._toggle_connection)
        connection_layout.addWidget(self.connection_label)
        connection_layout.addWidget(self.server_label)
        connection_layout.addWidget(self.connect_button)
        root.addWidget(connection_box)

        station_box = QGroupBox("Aktuelle Station")
        station_form = QFormLayout(station_box)
        self.callsign_label = QLabel("Nicht bekannt")
        self.name_label = QLabel("Nicht bekannt")
        self.dmr_id_label = QLabel("Kein aktiver Sprecher")
        self.target_label = QLabel("–")
        self.duration_label = QLabel("0 Sekunden")
        station_form.addRow("Rufzeichen:", self.callsign_label)
        station_form.addRow("Name:", self.name_label)
        station_form.addRow("DMR-ID:", self.dmr_id_label)
        station_form.addRow("Ziel:", self.target_label)
        station_form.addRow("Sprechdauer:", self.duration_label)
        root.addWidget(station_box)

        send_box = QGroupBox("Senden")
        send_layout = QVBoxLayout(send_box)
        self.ptt_button = QPushButton("PTT – Senden einschalten")
        self.ptt_button.setMinimumHeight(64)
        self.ptt_button.clicked.connect(self._toggle_tx)
        self.tx_status = QLabel("Senden nicht aktiv")
        self.encoder_status = QLabel("AMBE-Encoder wird geprüft …")
        send_layout.addWidget(self.ptt_button)
        send_layout.addWidget(self.tx_status)
        send_layout.addWidget(self.encoder_status)
        root.addWidget(send_box)
        root.addStretch(1)

        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage("Bereit")

    def _bind_shortcuts(self) -> None:
        QShortcut(QKeySequence("F5"), self, activated=self._toggle_connection)
        QShortcut(QKeySequence("Space"), self, activated=self._handle_space_shortcut)
        QShortcut(QKeySequence("Return"), self, activated=self._activate_focused_button)
        QShortcut(QKeySequence("Enter"), self, activated=self._activate_focused_button)
        QShortcut(QKeySequence("F6"), self, activated=self._toggle_timeslot)
        QShortcut(QKeySequence("F7"), self, activated=self._toggle_call_type)

    def _focused_button(self) -> QAbstractButton | None:
        """Liefert das aktuell fokussierte Qt-Schaltelement, falls vorhanden."""
        widget = QApplication.focusWidget()
        return widget if isinstance(widget, QAbstractButton) else None

    def _activate_focused_button(self) -> None:
        """Enter aktiviert nur das aktuell fokussierte Schaltelement."""
        button = self._focused_button()
        if button is not None and button.isEnabled():
            button.click()

    def _handle_space_shortcut(self) -> None:
        """Leertaste bedient fokussierte Buttons, sonst dient sie als PTT-Toggle."""
        button = self._focused_button()
        if button is not None:
            if button.isEnabled():
                button.click()
            return
        self._toggle_tx()

    def _sync_radio_tab_focus(self) -> None:
        """Macht beim Tabben nur den aktuell gewählten Radiobutton erreichbar.

        Qt synchronisiert diesen Startzustand nach einem manuellen Klick selbst.
        Beim ersten Programmstart war jedoch stets der erste Button der Gruppe
        im Tabpfad. Deshalb wird die Fokuspolicy nach dem Laden und nach jeder
        Auswahländerung ausdrücklich an den markierten Button gebunden.
        """
        for button in (self.ts1_radio, self.ts2_radio):
            button.setFocusPolicy(
                Qt.FocusPolicy.StrongFocus if button.isChecked() else Qt.FocusPolicy.ClickFocus
            )
        for button in (self.group_radio, self.private_radio):
            button.setFocusPolicy(
                Qt.FocusPolicy.StrongFocus if button.isChecked() else Qt.FocusPolicy.ClickFocus
            )

    def _target(self) -> tuple[int, int, str]:
        text = self.current_tg_label.text().strip()
        if not text or not text.isdigit() or int(text) <= 0:
            raise ValueError("Bitte eine gültige Talkgroup eingeben.")
        return int(text), 1 if self.ts1_radio.isChecked() else 2, "private" if self.private_radio.isChecked() else "group"

    def _focus_talkgroup(self) -> None:
        """Setzt nach dem Trennen den Fokus in das Feld für eine neue Talkgroup."""
        self.tg_edit.setFocus()
        self.tg_edit.selectAll()

    def _apply_pending_talkgroup(self) -> bool:
        """Übernimmt eine eingetragene neue TG, bevor verbunden wird."""
        if not self.tg_edit.text().strip():
            return True
        return self._apply_talkgroup_entry()

    def _apply_talkgroup_entry(self) -> bool:
        """Übernimmt die neue TG; Enter stellt noch keine Verbindung her."""
        text = self.tg_edit.text().strip()
        if not text:
            return True
        if not text.isdigit() or int(text) <= 0:
            QMessageBox.warning(self, "CarenDMR", "Bitte eine gültige Talkgroup eingeben.")
            return False
        self.current_tg_label.setText(str(int(text)))
        self.tg_edit.clear()
        try:
            self._save_preferences()
        except Exception as error:
            QMessageBox.warning(self, "CarenDMR", str(error))
            return False
        self.connect_button.setFocus()
        self.statusBar().showMessage(f"Talkgroup {self.current_tg_label.text()} übernommen.")
        return True

    def _save_preferences(self) -> None:
        tg, ts, call_type = self._target()
        self.preferences_store.save(OperatingPreferences(tg, ts, call_type, False))

    def _set_controls_for_state(self, state: RadioState) -> None:
        """Spiegelt den realen Betriebszustand vollständig in den Qt-Controls.

        Besonders wichtig: Während TRANSMITTING muss der PTT-Button aktiv
        bleiben. Nur so kann der zweite Klick beziehungsweise die Leertaste das
        laufende TX zuverlässig beenden.
        """
        editable = state in {RadioState.DISCONNECTED, RadioState.ERROR}
        self.tg_edit.setEnabled(editable)
        self.ts1_radio.setEnabled(editable)
        self.ts2_radio.setEnabled(editable)
        self.group_radio.setEnabled(editable)
        self.private_radio.setEnabled(editable)

        connected_or_tx = state in {RadioState.CONNECTED, RadioState.TRANSMITTING}
        self.ptt_button.setEnabled(connected_or_tx and self._encoder_ready)

        if state in {RadioState.CONNECTED, RadioState.TRANSMITTING}:
            self.connect_button.setText("Trennen")
        elif state is RadioState.CONNECTING:
            self.connect_button.setText("Verbindungsaufbau …")
        elif state is RadioState.DISCONNECTING:
            self.connect_button.setText("Trennen …")
        else:
            self.connect_button.setText("Verbinden")

        self.connect_button.setEnabled(
            state not in {RadioState.CONNECTING, RadioState.DISCONNECTING, RadioState.TRANSMITTING}
        )

    def _toggle_connection(self) -> None:
        state = self.radio_state.state
        if state in {RadioState.CONNECTED, RadioState.TRANSMITTING}:
            self._disconnect()
        elif state in {RadioState.DISCONNECTED, RadioState.ERROR}:
            if self._apply_pending_talkgroup():
                self._connect()

    def _connect(self) -> None:
        try:
            tg, ts, call_type = self._target()
            self._save_preferences()
        except Exception as error:
            QMessageBox.warning(self, "CarenDMR", str(error))
            return
        self.radio_state.synchronize(RadioState.CONNECTING)
        self.connection_label.setText("Verbindung wird hergestellt …")
        self.statusBar().showMessage("Verbindung wird hergestellt …")
        self._set_controls_for_state(self.radio_state.state)

        def worker() -> None:
            try:
                started = self.connection_manager.connect(tg, ts, call_type)
                self._updates.put(("connect_result", started))
            except Exception as error:
                self._updates.put(("connect_error", error))
        Thread(target=worker, name="CarenDMR-Qt-Connect", daemon=True).start()

    def _disconnect(self) -> None:
        if self._tx_active:
            self._stop_tx()
        self.radio_state.synchronize(RadioState.DISCONNECTING)
        self.statusBar().showMessage("Empfang und Verbindung werden beendet …")
        self._set_controls_for_state(self.radio_state.state)

        def worker() -> None:
            try:
                self.connection_manager.disconnect()
                self.receive_service.wait(8.0)
                self._updates.put(("disconnect_result", True))
            except Exception as error:
                self._updates.put(("disconnect_error", error))
        Thread(target=worker, name="CarenDMR-Qt-Disconnect", daemon=True).start()

    def _toggle_tx(self) -> None:
        if self._tx_active:
            self._stop_tx()
        else:
            self._start_tx()

    def _start_tx(self) -> None:
        if self.radio_state.state is not RadioState.CONNECTED:
            self.statusBar().showMessage("PTT ist nur bei aktiver Verbindung möglich.")
            return
        if not self._encoder_ready:
            self.statusBar().showMessage("AMBE-Encoder ist noch nicht bereit.")
            return
        self._tx_stop_event = Event()
        self._tx_active = True
        self.radio_state.synchronize(RadioState.TRANSMITTING)
        self.ptt_button.setText("PTT – Senden ausschalten")
        self.tx_status.setText("Senden aktiv")
        self.statusBar().showMessage("Senden aktiv")
        self._set_controls_for_state(self.radio_state.state)
        stop_event = self._tx_stop_event

        def worker() -> None:
            try:
                result = self.connection_manager.run_parrot_hold_to_talk(stop_event, optimize=True)
                self._updates.put(("tx_result", result))
            except Exception as error:
                self._updates.put(("tx_error", error))
        Thread(target=worker, name="CarenDMR-Qt-TX", daemon=True).start()

    def _stop_tx(self) -> None:
        if not self._tx_active:
            return
        if self._tx_stop_event is not None:
            self._tx_stop_event.set()
        # Der Worker beendet Aufnahme, TX und RX-Neustart. Der Button bleibt
        # bis zum Ergebnis sichtbar, wird aber gegen Mehrfachklicks gesperrt.
        self.ptt_button.setEnabled(False)
        self.ptt_button.setText("PTT – Sendung wird beendet …")
        self.tx_status.setText("Sendung wird beendet …")
        self.statusBar().showMessage("Sendung wird beendet …")

    def _finish_tx(self, message: str) -> None:
        self._tx_active = False
        self._tx_stop_event = None
        state = RadioState.CONNECTED if self.receive_service.is_running else RadioState.DISCONNECTED
        self.radio_state.synchronize(state)
        self.ptt_button.setText("PTT – Senden einschalten")
        self.tx_status.setText("Senden nicht aktiv")
        self.statusBar().showMessage(message)
        self._set_controls_for_state(state)

    def _verify_encoder(self) -> None:
        def worker() -> None:
            try:
                diagnostics = self.encoder_service.verify_configured()
                self._updates.put(("encoder_ready", diagnostics))
            except Exception as error:
                self._updates.put(("encoder_error", error))
        Thread(target=worker, name="CarenDMR-Qt-Encoder", daemon=True).start()

    def _toggle_timeslot(self) -> None:
        if self.radio_state.snapshot().can_edit_parameters:
            select_ts2 = self.ts1_radio.isChecked()
            self.ts2_radio.setChecked(select_ts2)
            self.ts1_radio.setChecked(not select_ts2)

    def _toggle_call_type(self) -> None:
        if not self.radio_state.snapshot().can_edit_parameters:
            return
        select_private = not self.private_radio.isChecked()
        self.private_radio.setChecked(select_private)
        self.group_radio.setChecked(not select_private)

    def _process_updates(self) -> None:
        try:
            while True:
                kind, value = self._updates.get_nowait()
                if kind == "state":
                    self._apply_state(value)
                elif kind == "connect_result":
                    if bool(value):
                        self.statusBar().showMessage("Empfang wird gestartet …")
                    elif self.receive_service.is_running:
                        self.radio_state.synchronize(RadioState.CONNECTED)
                elif kind == "connect_error":
                    self.radio_state.synchronize(RadioState.ERROR)
                    self.connection_label.setText("Verbindungsfehler")
                    self.statusBar().showMessage(f"Verbindungsfehler: {value}")
                    QMessageBox.critical(self, "CarenDMR", f"Verbindung fehlgeschlagen:\n\n{value}")
                    self._set_controls_for_state(self.radio_state.state)
                elif kind == "disconnect_result":
                    self.radio_state.synchronize(RadioState.DISCONNECTED)
                    self.statusBar().showMessage("Empfang und Verbindung beendet. Neue Talkgroup kann eingegeben werden.")
                    self._set_controls_for_state(self.radio_state.state)
                    QTimer.singleShot(0, self._focus_talkgroup)
                elif kind == "disconnect_error":
                    self.radio_state.synchronize(RadioState.ERROR)
                    self.statusBar().showMessage(f"Trennen fehlgeschlagen: {value}")
                elif kind == "encoder_ready":
                    self._encoder_ready = True
                    self.encoder_status.setText("AMBE-Encoder bereit")
                    self._set_controls_for_state(self.radio_state.state)
                elif kind == "encoder_error":
                    self._encoder_ready = False
                    self.encoder_status.setText(f"Senden gesperrt: {value}")
                    self._set_controls_for_state(self.radio_state.state)
                elif kind == "tx_result":
                    self._finish_tx("Sendung beendet; Empfang wieder aktiv.")
                elif kind == "tx_error":
                    self._finish_tx(f"Sendefehler: {value}")
                    QMessageBox.critical(self, "CarenDMR", f"Senden fehlgeschlagen:\n\n{value}")
        except queue.Empty:
            pass

    def _apply_state(self, state: ApplicationState) -> None:
        if state.connection is ConnectionState.CONNECTING:
            self.radio_state.synchronize(RadioState.CONNECTING)
        elif state.brandmeister_connected and state.receive_active:
            if not self._tx_active:
                self.radio_state.synchronize(RadioState.CONNECTED)
        elif state.connection is ConnectionState.ERROR:
            self.radio_state.synchronize(RadioState.ERROR)
        elif not state.receive_active and not self._tx_active and self.radio_state.state not in {RadioState.CONNECTING, RadioState.DISCONNECTING}:
            self.radio_state.synchronize(RadioState.DISCONNECTED)

        self.connection_label.setText(state.connection.value)
        self.server_label.setText(f"Server: {state.server if state.brandmeister_connected else 'Nicht verbunden'}")
        if state.talkgroup:
            self.current_tg_label.setText(str(state.talkgroup))
        if state.brandmeister_connected and state.receive_active and not self._tx_active:
            self.tx_status.setText("Senden nicht aktiv")
            self.statusBar().showMessage("Empfang aktiv")
        call = state.current_call
        if call is None:
            self.callsign_label.setText("Nicht bekannt")
            self.name_label.setText("Nicht bekannt")
            self.dmr_id_label.setText("Kein aktiver Sprecher")
            self.target_label.setText(f"Talkgroup {state.talkgroup}, Timeslot {state.timeslot}")
            self.duration_label.setText("0 Sekunden")
        else:
            contact = call.contact
            self.callsign_label.setText(contact.callsign if contact else "Nicht gefunden")
            self.name_label.setText(contact.display_name if contact and contact.display_name else "Nicht angegeben")
            self.dmr_id_label.setText(str(call.source_id))
            self.target_label.setText(f"Talkgroup {call.talkgroup}, Timeslot {call.timeslot}")
            self.duration_label.setText(f"{call.elapsed_seconds:.0f} Sekunden")
        self._set_controls_for_state(self.radio_state.state)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._tx_active and self._tx_stop_event is not None:
            self._tx_stop_event.set()
        self.connection_manager.disconnect()
        self.receive_service.wait(3.0)
        event.accept()


def run_gui(project_root: Path) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow(project_root)
    window.show()
    return int(app.exec())
