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
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence, QRegularExpressionValidator, QShortcut
from PySide6.QtWidgets import (
    QApplication, QAbstractButton, QButtonGroup, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QRadioButton,
    QStatusBar, QTabWidget, QVBoxLayout, QWidget, QSlider, QCheckBox, QGridLayout,
    QFrame, QSizePolicy,
)

from carendmr.application import (
    AudioSendService, ConnectionManager, EncoderService, EventService,
    ParrotTestService, RadioState, RadioStateMachine, ReceiveService,
)
from carendmr.application.operating_preferences import OperatingPreferences, OperatingPreferencesStore
from carendmr.domain import ApplicationState, ConnectionState
from carendmr.version import __version__
from carendmr.ui_qt.theme import METRICS
from carendmr.accessibility.hotkeys import HotkeyManager
from carendmr.ui_qt.settings_dialog import SettingsDialog
from carendmr.ui_qt.history_widget import QsoHistoryWidget
from carendmr.ui_qt.theme import apply_theme


class MainWindow(QMainWindow):
    def __init__(self, project_root: Path) -> None:
        super().__init__()
        self.project_root = Path(project_root)
        self.setWindowTitle(f"CarenDMR {__version__} – Funkgerät auf dem Desktop")
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
        self._settings_dialog: SettingsDialog | None = None
        self.hotkey_manager = HotkeyManager(self.project_root / "config" / "hotkeys.local.json")
        self._shortcuts: list[QShortcut] = []

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
        """Baut das Layout V1, ohne die vorhandene Bedienlogik zu verändern."""
        self.tabs = QTabWidget(self)
        self.tabs.setObjectName("mainTabs")
        operation_page = QWidget(self.tabs)
        operation_page.setObjectName("operationPage")
        root = QVBoxLayout(operation_page)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(12)

        # Kopfzeile: keine neue Funktion, nur eine klare visuelle Hierarchie.
        header = QFrame(operation_page)
        header.setObjectName("headerCard")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 12, 18, 12)
        title = QLabel("CarenDMR")
        title.setObjectName("appTitle")
        subtitle = QLabel("Funkgerät auf dem Desktop")
        subtitle.setObjectName("appSubtitle")
        title_column = QVBoxLayout()
        title_column.setSpacing(0)
        title_column.addWidget(title)
        title_column.addWidget(subtitle)
        header_layout.addLayout(title_column)
        header_layout.addStretch(1)
        self.connection_label = QLabel("Getrennt")
        self.connection_label.setObjectName("connectionBadge")
        self.connection_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.connection_label.setFixedSize(METRICS.connection_control_width, METRICS.status_control_height)
        header_layout.addWidget(self.connection_label)
        root.addWidget(header)

        content = QGridLayout()
        content.setHorizontalSpacing(12)
        content.setVerticalSpacing(12)
        content.setColumnStretch(0, 3)
        content.setColumnStretch(1, 2)
        root.addLayout(content, 1)

        # Funkziel und Verbindung.
        target_card = QFrame(operation_page)
        target_card.setObjectName("card")
        target_layout = QGridLayout(target_card)
        target_layout.setContentsMargins(18, 14, 18, 14)
        target_layout.setHorizontalSpacing(12)
        target_layout.setVerticalSpacing(8)
        target_heading = QLabel("FUNKZIEL")
        target_heading.setObjectName("sectionTitle")
        target_layout.addWidget(target_heading, 0, 0, 1, 6)

        current_caption = QLabel("Aktuelle TG")
        current_caption.setObjectName("fieldCaption")
        self.current_tg_label = QLabel(str(self.preferences.talkgroup))
        self.current_tg_label.setObjectName("currentTalkgroup")
        current_column = QVBoxLayout()
        current_column.setSpacing(1)
        current_column.addWidget(current_caption)
        current_column.addWidget(self.current_tg_label)
        target_layout.addLayout(current_column, 1, 0, 2, 1)

        target_layout.addWidget(QLabel("Neue Talkgroup"), 1, 1, 1, 2)
        self.tg_edit = QLineEdit()
        self.tg_edit.setObjectName("talkgroupInput")
        self.tg_edit.setPlaceholderText("Neue TG eingeben")
        self.tg_edit.setMaxLength(8)
        self.tg_edit.setValidator(QRegularExpressionValidator(QRegularExpression(r"[0-9]{0,8}"), self.tg_edit))
        target_layout.addWidget(self.tg_edit, 2, 1, 1, 2)

        self.ts1_radio = QRadioButton("TS 1")
        self.ts2_radio = QRadioButton("TS 2")
        self.ts_group = QButtonGroup(self)
        self.ts_group.addButton(self.ts1_radio, 1)
        self.ts_group.addButton(self.ts2_radio, 2)
        (self.ts1_radio if self.preferences.timeslot == 1 else self.ts2_radio).setChecked(True)
        ts_column = QVBoxLayout()
        ts_column.setSpacing(3)
        ts_column.addWidget(QLabel("Timeslot"))
        ts_row = QHBoxLayout()
        ts_row.setSpacing(10)
        ts_row.addWidget(self.ts1_radio)
        ts_row.addWidget(self.ts2_radio)
        ts_column.addLayout(ts_row)
        target_layout.addLayout(ts_column, 1, 3, 2, 1)

        self.group_radio = QRadioButton("Gruppe")
        self.private_radio = QRadioButton("Privat")
        self.call_group = QButtonGroup(self)
        self.call_group.addButton(self.group_radio)
        self.call_group.addButton(self.private_radio)
        (self.private_radio if self.preferences.call_type == "private" else self.group_radio).setChecked(True)
        call_column = QVBoxLayout()
        call_column.setSpacing(3)
        call_column.addWidget(QLabel("Rufart"))
        call_row = QHBoxLayout()
        call_row.setSpacing(10)
        call_row.addWidget(self.group_radio)
        call_row.addWidget(self.private_radio)
        call_column.addLayout(call_row)
        target_layout.addLayout(call_column, 1, 4, 2, 1)

        self.connect_button = QPushButton("Verbinden")
        self.connect_button.setObjectName("connectButton")
        self.connect_button.setFixedSize(METRICS.connection_control_width, METRICS.action_control_height)
        self.connect_button.clicked.connect(self._toggle_connection)
        target_layout.addWidget(self.connect_button, 1, 5, 2, 1)
        self.server_label = QLabel("Server: Nicht verbunden")
        self.server_label.setObjectName("secondaryText")
        target_layout.addWidget(self.server_label, 3, 0, 1, 6)

        self.ts1_radio.toggled.connect(self._sync_radio_tab_focus)
        self.ts2_radio.toggled.connect(self._sync_radio_tab_focus)
        self.group_radio.toggled.connect(self._sync_radio_tab_focus)
        self.private_radio.toggled.connect(self._sync_radio_tab_focus)
        self._sync_radio_tab_focus()
        content.addWidget(target_card, 0, 0, 1, 2)

        # Aktuelle Station: wichtigste Empfangsinformationen prominent, Details kompakt.
        station_card = QFrame(operation_page)
        station_card.setObjectName("card")
        station_layout = QGridLayout(station_card)
        station_layout.setContentsMargins(18, 14, 18, 14)
        station_layout.setHorizontalSpacing(14)
        station_layout.setVerticalSpacing(5)
        station_heading = QLabel("AKTUELLE STATION")
        station_heading.setObjectName("sectionTitle")
        station_layout.addWidget(station_heading, 0, 0, 1, 4)
        self.callsign_label = QLabel("Nicht bekannt")
        self.callsign_label.setObjectName("callsignDisplay")
        self.name_label = QLabel("Nicht bekannt")
        self.name_label.setObjectName("stationName")
        station_layout.addWidget(self.callsign_label, 1, 0, 1, 4)
        station_layout.addWidget(self.name_label, 2, 0, 1, 4)
        self.location_label = QLabel("Nicht bekannt")
        self.country_label = QLabel("Nicht bekannt")
        self.dmr_id_label = QLabel("Kein aktiver Sprecher")
        self.target_label = QLabel("–")
        self.duration_label = QLabel("0 Sekunden")
        self.qso_status_label = QLabel("Keine Station aktiv")
        self.qso_status_label.setObjectName("qsoStatus")
        detail_labels = (
            ("Ort/Region", self.location_label), ("Land", self.country_label),
            ("DMR-ID", self.dmr_id_label), ("Ziel", self.target_label),
            ("Sprechdauer", self.duration_label), ("QSO-Status", self.qso_status_label),
        )
        for index, (caption, value) in enumerate(detail_labels):
            row = 3 + index // 2
            column = (index % 2) * 2
            cap = QLabel(caption)
            cap.setObjectName("fieldCaption")
            station_layout.addWidget(cap, row, column)
            station_layout.addWidget(value, row, column + 1)
        content.addWidget(station_card, 1, 0)

        # Rechte Bedienkarte: tägliche Audiofunktionen und PTT, ohne neue Controls.
        control_card = QFrame(operation_page)
        control_card.setObjectName("card")
        control_layout = QVBoxLayout(control_card)
        control_layout.setContentsMargins(18, 14, 18, 14)
        control_layout.setSpacing(9)
        control_heading = QLabel("FUNK- UND AUDIOBEDIENUNG")
        control_heading.setObjectName("sectionTitle")
        control_layout.addWidget(control_heading)

        self.operation_gain_slider = QSlider(Qt.Orientation.Horizontal)
        self.operation_gain_slider.setRange(0, 100)
        self.operation_gain_value = QLabel("100 %")
        self.operation_gain_value.setObjectName("valueLabel")
        gain_row = QGridLayout()
        gain_row.addWidget(QLabel("Mic-Gain"), 0, 0)
        gain_row.addWidget(self.operation_gain_value, 0, 1, alignment=Qt.AlignmentFlag.AlignRight)
        gain_row.addWidget(self.operation_gain_slider, 1, 0, 1, 2)
        control_layout.addLayout(gain_row)

        self.operation_volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.operation_volume_slider.setRange(0, 100)
        self.operation_volume_value = QLabel("100 %")
        self.operation_volume_value.setObjectName("valueLabel")
        volume_row = QGridLayout()
        volume_row.addWidget(QLabel("RX-Lautstärke"), 0, 0)
        volume_row.addWidget(self.operation_volume_value, 0, 1, alignment=Qt.AlignmentFlag.AlignRight)
        volume_row.addWidget(self.operation_volume_slider, 1, 0, 1, 2)
        control_layout.addLayout(volume_row)

        checks = QHBoxLayout()
        self.operation_muted_check = QCheckBox("Empfang stumm")
        self.operation_agc_check = QCheckBox("AGC aktiv")
        checks.addWidget(self.operation_muted_check)
        checks.addWidget(self.operation_agc_check)
        checks.addStretch(1)
        control_layout.addLayout(checks)

        self.ptt_button = QPushButton("PTT – Senden einschalten")
        self.ptt_button.setObjectName("pttButton")
        self.ptt_button.setMinimumHeight(74)
        self.ptt_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.ptt_button.clicked.connect(self._toggle_tx)
        self.tx_status = QLabel("Senden nicht aktiv")
        self.tx_status.setObjectName("txStatus")
        self.tx_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.encoder_status = QLabel("AMBE-Encoder wird geprüft …")
        self.encoder_status.setObjectName("secondaryText")
        self.encoder_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        control_layout.addStretch(1)
        control_layout.addWidget(self.ptt_button)
        control_layout.addWidget(self.tx_status)
        control_layout.addWidget(self.encoder_status)
        content.addWidget(control_card, 1, 1)

        # Betriebsinformationen nur einmal und bewusst kompakt.
        info_card = QFrame(operation_page)
        info_card.setObjectName("card")
        info_layout = QGridLayout(info_card)
        info_layout.setContentsMargins(18, 11, 18, 11)
        info_layout.setHorizontalSpacing(14)
        info_heading = QLabel("BETRIEBSINFORMATIONEN")
        info_heading.setObjectName("sectionTitle")
        info_layout.addWidget(info_heading, 0, 0, 1, 4)
        self.audio_status_label = QLabel("Audio nicht aktiv")
        self.statistics_label = QLabel("0 Datagramme, 0 Sprachbursts, 0 Decodierfehler")
        self.last_event_label = QLabel("Bereit")
        self.last_event_label.setWordWrap(True)
        info_layout.addWidget(QLabel("Audio"), 1, 0)
        info_layout.addWidget(self.audio_status_label, 1, 1)
        info_layout.addWidget(QLabel("Empfang"), 1, 2)
        info_layout.addWidget(self.statistics_label, 1, 3)
        info_layout.addWidget(QLabel("Letztes Ereignis"), 2, 0)
        info_layout.addWidget(self.last_event_label, 2, 1, 1, 3)
        content.addWidget(info_card, 2, 0, 1, 2)

        self.operation_gain_slider.valueChanged.connect(self._operation_gain_changed)
        self.operation_volume_slider.valueChanged.connect(self._operation_volume_changed)
        self.operation_muted_check.toggled.connect(self._operation_muted_changed)
        self.operation_agc_check.toggled.connect(self._operation_agc_changed)
        self._sync_operation_audio_controls()

        self.tabs.addTab(operation_page, "Betrieb")
        self.history_widget = QsoHistoryWidget(
            self.receive_service.history,
            self._show_status,
            self._history_worked_changed,
            self.tabs,
        )
        self.tabs.addTab(self.history_widget, "QSO-Historie")
        self.tabs.currentChanged.connect(self._tab_changed)
        self.setCentralWidget(self.tabs)
        self._build_menu()
        self.setStatusBar(QStatusBar(self))
        self.statusBar().setObjectName("mainStatusBar")
        self.statusBar().showMessage("Bereit")
        self._apply_theme()
        self._restore_tab_order()

    def _apply_theme(self) -> None:
        """Theme wird zentral auf QApplication-Ebene verwaltet."""
        app = QApplication.instance()
        if app is not None:
            apply_theme(app)

    def _restore_tab_order(self) -> None:
        """Bewahrt die etablierte Tastaturreihenfolge trotz neuem Layout."""
        selected_ts = self.ts1_radio if self.ts1_radio.isChecked() else self.ts2_radio
        selected_call = self.private_radio if self.private_radio.isChecked() else self.group_radio
        QWidget.setTabOrder(self.tg_edit, selected_ts)
        QWidget.setTabOrder(selected_ts, selected_call)
        QWidget.setTabOrder(selected_call, self.connect_button)
        QWidget.setTabOrder(self.connect_button, self.operation_gain_slider)
        QWidget.setTabOrder(self.operation_gain_slider, self.operation_volume_slider)
        QWidget.setTabOrder(self.operation_volume_slider, self.operation_muted_check)
        QWidget.setTabOrder(self.operation_muted_check, self.operation_agc_check)
        QWidget.setTabOrder(self.operation_agc_check, self.ptt_button)


    def _show_status(self, message: str) -> None:
        self.statusBar().showMessage(message)

    def _history_worked_changed(self, source_id: int, worked: bool) -> None:
        """Synchronisiert eine Historienänderung sofort mit der Betriebsseite."""
        state = self.receive_service.state_store.get()
        call = state.current_call
        if call is not None and call.source_id == source_id:
            self.qso_status_label.setText(
                "Bereits gesprochen" if worked else "Noch nicht gesprochen"
            )


    def _tab_changed(self, index: int) -> None:
        if hasattr(self, "history_widget") and self.tabs.widget(index) is self.history_widget:
            self.history_widget.refresh()

    def _build_menu(self) -> None:
        """Ergänzt nur den Zugang zum separaten Einstellungsfenster."""
        program_menu = self.menuBar().addMenu("Programm")
        settings_action = QAction("Einstellungen …", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self._open_settings)
        program_menu.addAction(settings_action)

    def _open_settings(self) -> None:
        if self._settings_dialog is not None and self._settings_dialog.isVisible():
            self._settings_dialog.raise_()
            self._settings_dialog.activateWindow()
            return
        dialog = SettingsDialog(
            self.project_root, self.audio_send_service, self.receive_service, self
        )
        dialog.settings_applied.connect(self._settings_applied)
        dialog.finished.connect(lambda _result: setattr(self, "_settings_dialog", None))
        self._settings_dialog = dialog
        dialog.show()


    def _settings_applied(self) -> None:
        self._reload_hotkeys()
        self._sync_operation_audio_controls()

    def _sync_operation_audio_controls(self) -> None:
        for widget in (getattr(self, "operation_gain_slider", None), getattr(self, "operation_volume_slider", None),
                       getattr(self, "operation_muted_check", None), getattr(self, "operation_agc_check", None)):
            if widget is not None:
                widget.blockSignals(True)
        try:
            self.operation_gain_slider.setValue(int(self.audio_send_service.gain_percent))
            self.operation_volume_slider.setValue(min(100, int(self.audio_send_service.output_volume_percent)))
            self.operation_muted_check.setChecked(bool(self.audio_send_service.user_muted))
            self.operation_agc_check.setChecked(bool(self.audio_send_service.agc_enabled))
            self.operation_gain_value.setText(f"{int(self.audio_send_service.gain_percent)} %")
            self.operation_volume_value.setText(f"{min(100, int(self.audio_send_service.output_volume_percent))} %")
        finally:
            for widget in (self.operation_gain_slider, self.operation_volume_slider, self.operation_muted_check, self.operation_agc_check):
                widget.blockSignals(False)

    def _save_operation_audio(self) -> None:
        try:
            self.audio_send_service.save_settings()
        except Exception as exc:
            self.statusBar().showMessage(f"Audioeinstellung konnte nicht gespeichert werden: {exc}")

    def _operation_gain_changed(self, value: int) -> None:
        self.operation_gain_value.setText(f"{value} %")
        self.audio_send_service.set_gain_percent(value)
        self._save_operation_audio()

    def _operation_volume_changed(self, value: int) -> None:
        self.operation_volume_value.setText(f"{value} %")
        self.audio_send_service.set_output_volume_percent(value)
        self.receive_service.set_output_volume_percent(value)
        self._save_operation_audio()

    def _operation_muted_changed(self, checked: bool) -> None:
        self.audio_send_service.set_user_muted(checked)
        self.receive_service.set_user_muted(checked)
        self._save_operation_audio()
        self.statusBar().showMessage("Empfang stumm" if checked else "Empfangston aktiv")

    def _operation_agc_changed(self, checked: bool) -> None:
        self.audio_send_service.set_agc_enabled(checked)
        self.receive_service.set_agc_enabled(checked)
        self._save_operation_audio()
        self.statusBar().showMessage("AGC aktiv" if checked else "AGC ausgeschaltet")

    def _bind_shortcuts(self) -> None:
        for shortcut in self._shortcuts:
            shortcut.setEnabled(False)
            shortcut.deleteLater()
        self._shortcuts.clear()
        actions = {
            "TG_CHANGE": self._focus_talkgroup,
            "CONNECT": self._toggle_connection,
            "TS_CHANGE": self._toggle_timeslot,
            "CALLTYPE_CHANGE": self._toggle_call_type,
            "OPEN_OPERATION": self._open_operation,
            "OPEN_HISTORY": self._open_history,
            "OPEN_SETTINGS": self._open_settings,
            "CONFIRM_QSO": self._confirm_selected_qso,
            "PTT": self._handle_space_shortcut,
        }
        for function, callback in actions.items():
            sequence = self.hotkey_manager.mapping.get(function, "")
            if not sequence:
                continue
            shortcut = QShortcut(QKeySequence(sequence), self, activated=callback)
            self._shortcuts.append(shortcut)
        for sequence in ("Return", "Enter"):
            self._shortcuts.append(QShortcut(QKeySequence(sequence), self, activated=self._activate_focused_button))

    def _open_operation(self) -> None:
        self.tabs.setCurrentIndex(0)
        self.tg_edit.setFocus()

    def _open_history(self) -> None:
        self.tabs.setCurrentWidget(self.history_widget)
        self.history_widget.refresh()
        self.history_widget.table.setFocus()

    def _confirm_selected_qso(self) -> None:
        if self.tabs.currentWidget() is self.history_widget:
            self.history_widget.toggle_worked()

    def _reload_hotkeys(self) -> None:
        self.hotkey_manager.load()
        self._bind_shortcuts()
        self.statusBar().showMessage("Hotkeys wurden übernommen.")

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
        self.connect_button.setProperty(
            "visualState", "disconnect" if state in {RadioState.CONNECTED, RadioState.TRANSMITTING} else "connect"
        )
        if state is RadioState.TRANSMITTING:
            badge_state = "tx"
        elif state is RadioState.CONNECTED:
            badge_state = "connected"
        elif state in {RadioState.CONNECTING, RadioState.DISCONNECTING}:
            badge_state = "busy"
        else:
            badge_state = "disconnected"
        self.connection_label.setProperty("visualState", badge_state)
        for widget in (self.connect_button, self.connection_label):
            widget.style().unpolish(widget)
            widget.style().polish(widget)

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
        self.ptt_button.setProperty("visualState", "tx")
        self.ptt_button.style().unpolish(self.ptt_button)
        self.ptt_button.style().polish(self.ptt_button)
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
        self.ptt_button.setProperty("visualState", "ending")
        self.ptt_button.style().unpolish(self.ptt_button)
        self.ptt_button.style().polish(self.ptt_button)
        self.tx_status.setText("Sendung wird beendet …")
        self.statusBar().showMessage("Sendung wird beendet …")

    def _finish_tx(self, message: str) -> None:
        self._tx_active = False
        self._tx_stop_event = None
        state = RadioState.CONNECTED if self.receive_service.is_running else RadioState.DISCONNECTED
        self.radio_state.synchronize(state)
        self.ptt_button.setText("PTT – Senden einschalten")
        self.ptt_button.setProperty("visualState", "idle")
        self.ptt_button.style().unpolish(self.ptt_button)
        self.ptt_button.style().polish(self.ptt_button)
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
                elif kind == "event":
                    self.last_event_label.setText(str(getattr(value, "message", value)))
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
        self.audio_status_label.setText("Audio aktiv" if state.audio_active else "Audio nicht aktiv")
        stats = state.statistics
        self.statistics_label.setText(
            f"{stats.datagrams} Datagramme, {stats.voice_bursts} Sprachbursts, "
            f"{stats.decoded_codewords} Codewörter, {stats.decode_errors} Decodierfehler"
        )
        if state.message:
            self.last_event_label.setText(state.message)
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
            self.location_label.setText("Nicht bekannt")
            self.country_label.setText("Nicht bekannt")
            self.target_label.setText(f"Talkgroup {state.talkgroup}, Timeslot {state.timeslot}")
            self.duration_label.setText("0 Sekunden")
            self.qso_status_label.setText("Keine Station aktiv")
        else:
            contact = call.contact
            self.callsign_label.setText(contact.callsign if contact else "Nicht gefunden")
            self.name_label.setText(contact.display_name if contact and contact.display_name else "Nicht angegeben")
            self.dmr_id_label.setText(str(call.source_id))
            location = ", ".join(part for part in (contact.city, contact.state) if contact and part) if contact else ""
            self.location_label.setText(location or "Nicht angegeben")
            self.country_label.setText(contact.country if contact and contact.country else "Nicht angegeben")
            self.target_label.setText(f"Talkgroup {call.talkgroup}, Timeslot {call.timeslot}")
            self.duration_label.setText(f"{call.elapsed_seconds:.0f} Sekunden")
            self.qso_status_label.setText(
                "Bereits gesprochen"
                if self.receive_service.history.is_worked(call.source_id)
                else "Noch nicht gesprochen"
            )
        self._set_controls_for_state(self.radio_state.state)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._tx_active and self._tx_stop_event is not None:
            self._tx_stop_event.set()
        self.connection_manager.disconnect()
        self.receive_service.wait(3.0)
        event.accept()


def run_gui(project_root: Path) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    apply_theme(app)
    window = MainWindow(project_root)
    window.show()
    return int(app.exec())
