"""Extrem reduzierte Qt-Oberfläche für den täglichen CarenDMR-Funkbetrieb.

Die Easy-Oberfläche enthält bewusst keine eigene Funklogik. Alle Befehle für
Verbinden, Trennen und PTT laufen über den GUI-unabhängigen OperatingController
und damit über denselben stabilen ConnectionManager/RX/TX-Pfad wie die
Desktop-Oberfläche.
"""
from __future__ import annotations

import queue
import sys
from pathlib import Path
from threading import Event, Thread

from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from carendmr.application import RadioState
from carendmr.bootstrap import RadioCore, build_radio_core
from carendmr.application.operating_preferences import OperatingPreferences, OperatingPreferencesStore
from carendmr.ui_qt.accessibility_manager import AccessibilityManager
from carendmr.ui_qt.audio_cue import AudioCuePlayer
from carendmr.ui_qt.theme import apply_theme
from carendmr.version import __version__


class EasyButton(QPushButton):
    """QPushButton, der Enter und Leertaste gleichwertig akzeptiert."""

    def keyPressEvent(self, event) -> None:
        if event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter}:
            self.click()
            event.accept()
            return
        super().keyPressEvent(event)


class EasyWindow(QMainWindow):
    """Minimaler, vollständig tastaturbedienbarer DMR-Betrieb."""

    def __init__(self, project_root: Path, core: RadioCore | None = None) -> None:
        super().__init__()
        self.project_root = Path(project_root)
        self.setWindowTitle(f"CarenDMR Easy {__version__}")
        self.resize(680, 520)

        self.preferences_store = OperatingPreferencesStore(
            self.project_root / "config" / "operating.local.json"
        )
        self.preferences = self.preferences_store.load()
        self._timeslot = self.preferences.timeslot
        self._call_type = self.preferences.call_type

        # Identischer Funkkern wie in der Desktop-UI aus dem gemeinsamen Startpunkt.
        self.radio_core = core or build_radio_core(self.project_root)
        self.events = self.radio_core.events
        self.receive_service = self.radio_core.receive_service
        self.encoder_service = self.radio_core.encoder_service
        self.audio_send_service = self.radio_core.audio_send_service
        self.parrot_service = self.radio_core.parrot_service
        self.connection_manager = self.radio_core.connection_manager
        self.controller = self.radio_core.controller

        self.accessibility = AccessibilityManager()
        self.audio_cues = AudioCuePlayer(self.audio_send_service)
        self._updates: queue.SimpleQueue[tuple[str, object]] = queue.SimpleQueue()
        self._encoder_ready = False
        self._tx_pending = False
        self._tx_active = False
        self._tx_stopping = False
        self._tx_stop_event: Event | None = None
        self._last_radio_state = RadioState.DISCONNECTED
        self._connect_requested = False
        self._shortcuts: list[QShortcut] = []

        self._build_ui()
        self._bind_shortcuts()
        self.controller.subscribe(lambda snapshot: self._updates.put(("radio_state", snapshot.state)))

        self._timer = QTimer(self)
        self._timer.setInterval(80)
        self._timer.timeout.connect(self._process_updates)
        self._timer.start()

        self._apply_radio_state(self.controller.snapshot().state)
        QTimer.singleShot(0, self._focus_talkgroup)
        QTimer.singleShot(0, self._verify_encoder)

    def _build_ui(self) -> None:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        title = QLabel("CarenDMR Easy")
        title.setAccessibleName("CarenDMR Easy")
        layout.addWidget(title)

        self.channel_label = QLabel()
        self.channel_label.setObjectName("easyChannelLabel")
        self.channel_label.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.channel_label)

        self.status_label = QLabel("Getrennt")
        self.status_label.setObjectName("easyStatusLabel")
        self.status_label.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.status_label.setAccessibleName("Funkstatus")
        layout.addWidget(self.status_label)

        self.audio_level_label = QLabel()
        self.audio_level_label.setObjectName("easyAudioLevelLabel")
        self.audio_level_label.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.audio_level_label.setAccessibleName("Audiopegel")
        layout.addWidget(self.audio_level_label)
        self._refresh_audio_level_label()

        self.talkgroup_edit = QLineEdit(self._spaced_digits(self.preferences.talkgroup))
        self.talkgroup_edit.setObjectName("easyTalkgroupEdit")
        self.talkgroup_edit.setPlaceholderText("Talkgroup")
        self.talkgroup_edit.setAccessibleName("Talkgroup")
        self.talkgroup_edit.setAccessibleDescription("")
        self.talkgroup_edit.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.talkgroup_edit.editingFinished.connect(self._format_talkgroup_for_speech)
        self.talkgroup_edit.returnPressed.connect(self._focus_connect)
        layout.addWidget(self.talkgroup_edit)

        self.connect_button = EasyButton("Verbinden")
        self.connect_button.setObjectName("easyConnectButton")
        self.connect_button.setMinimumHeight(72)
        self.connect_button.setAccessibleName("Verbinden")
        self.connect_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.connect_button.clicked.connect(self._toggle_connection)
        layout.addWidget(self.connect_button)

        self.ptt_button = EasyButton("PTT")
        self.ptt_button.setObjectName("easyPttButton")
        self.ptt_button.setMinimumHeight(150)
        self.ptt_button.setAccessibleName("PTT")
        self.ptt_button.setAccessibleDescription("")
        self.ptt_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.ptt_button.clicked.connect(self._toggle_tx)
        layout.addWidget(self.ptt_button)

        self.exit_button = EasyButton("Beenden")
        self.exit_button.setObjectName("easyExitButton")
        self.exit_button.setMinimumHeight(72)
        self.exit_button.setAccessibleName("CarenDMR Easy beenden")
        self.exit_button.setAccessibleDescription(
            "Beendet CarenDMR. Eine aktive Funkverbindung wird vorher getrennt."
        )
        self.exit_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.exit_button.clicked.connect(self._exit_application)
        layout.addWidget(self.exit_button)

        help_label = QLabel(
            "Strg+T Timeslot · Strg+R Gruppe/Privat · Strg+Plus/Minus RX · Alt+Plus/Minus TX · F4 Status"
        )
        help_label.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(help_label)
        layout.addStretch(1)

        self.setCentralWidget(page)
        # Easy braucht unabhängig vom nativen macOS-Qt-Stil eine klar sichtbare
        # Tastaturfokus-Markierung.
        page.setStyleSheet("""
            QLineEdit#easyTalkgroupEdit:focus {
                border: 5px solid #FFD54A;
                padding: 3px 5px;
                background-color: #202C3A;
            }
            QPushButton#easyConnectButton:focus,
            QPushButton#easyPttButton:focus,
            QPushButton#easyExitButton:focus {
                border: 5px solid #FFD54A;
                padding: 4px 11px;
                background-color: #344457;
            }
        """)
        QWidget.setTabOrder(self.talkgroup_edit, self.connect_button)
        QWidget.setTabOrder(self.connect_button, self.ptt_button)
        QWidget.setTabOrder(self.ptt_button, self.exit_button)
        for control in (
            self.talkgroup_edit,
            self.connect_button,
            self.ptt_button,
            self.exit_button,
        ):
            control.installEventFilter(self)
        self._refresh_channel_label()

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        """Erzwingt in Easy eine verlässliche TAB-/Shift+TAB-Navigation.

        Das umgeht plattformspezifische Unterschiede der nativen macOS-
        Tastaturnavigation. Es werden nur TAB und Shift+TAB ohne weitere
        Modifikatortasten behandelt; alle anderen Tasten bleiben bei Qt.
        """
        controls = (self.talkgroup_edit, self.connect_button, self.ptt_button, self.exit_button)
        if watched in controls and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            modifiers = event.modifiers()
            backwards = key == Qt.Key.Key_Backtab or (
                key == Qt.Key.Key_Tab and bool(modifiers & Qt.KeyboardModifier.ShiftModifier)
            )
            plain_tab = key == Qt.Key.Key_Tab and modifiers in (
                Qt.KeyboardModifier.NoModifier,
                Qt.KeyboardModifier.ShiftModifier,
            )
            if key == Qt.Key.Key_Backtab or plain_tab:
                available = [control for control in controls if control.isEnabled() and control.isVisible()]
                if len(available) > 1:
                    try:
                        index = available.index(watched)
                    except ValueError:
                        index = 0
                    step = -1 if backwards else 1
                    target = available[(index + step) % len(available)]
                    reason = (
                        Qt.FocusReason.BacktabFocusReason
                        if backwards
                        else Qt.FocusReason.TabFocusReason
                    )
                    target.setFocus(reason)
                    event.accept()
                    return True
        return super().eventFilter(watched, event)

    def _bind_shortcuts(self) -> None:
        for key, handler in (
            ("Ctrl+T", self._toggle_timeslot),
            ("Ctrl+R", self._toggle_call_type),
            ("Ctrl++", self._rx_volume_up),
            ("Ctrl+-", self._rx_volume_down),
            ("Alt++", self._tx_level_up),
            ("Alt+-", self._tx_level_down),
            ("F4", self._announce_status),
        ):
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(handler)
            self._shortcuts.append(shortcut)

    def _refresh_audio_level_label(self) -> None:
        self.audio_level_label.setText(
            f"RX {int(self.audio_send_service.output_volume_percent)} % · "
            f"TX {int(self.audio_send_service.gain_percent)} %"
        )

    def _announce_audio_level(self, text: str, channel: str) -> None:
        self._refresh_audio_level_label()
        self.accessibility.announcer.announce(
            self.audio_level_label, text, channel=channel
        )

    def _set_rx_volume(self, value: int) -> None:
        value = max(0, min(200, int(value)))
        self.audio_send_service.set_output_volume_percent(value)
        self.receive_service.set_output_volume_percent(value)
        self.audio_send_service.save_settings()
        self._announce_audio_level(f"RX-Lautstärke {value} Prozent", "easy-rx-level")

    def _rx_volume_up(self) -> None:
        self._set_rx_volume(self.audio_send_service.output_volume_percent + 10)

    def _rx_volume_down(self) -> None:
        self._set_rx_volume(self.audio_send_service.output_volume_percent - 10)

    def _set_tx_level(self, value: int) -> None:
        value = max(0, min(100, int(value)))
        self.audio_send_service.set_gain_percent(value)
        self.audio_send_service.save_settings()
        self._announce_audio_level(f"TX-Pegel {value} Prozent", "easy-tx-level")

    def _tx_level_up(self) -> None:
        self._set_tx_level(self.audio_send_service.gain_percent + 10)

    def _tx_level_down(self) -> None:
        self._set_tx_level(self.audio_send_service.gain_percent - 10)

    def _focus_talkgroup(self) -> None:
        self.talkgroup_edit.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self.talkgroup_edit.selectAll()

    def _focus_connect(self) -> None:
        if self.connect_button.isEnabled():
            self.connect_button.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def _focus_ptt(self) -> None:
        if self.ptt_button.isEnabled():
            self.ptt_button.setFocus(Qt.FocusReason.ShortcutFocusReason)

    @staticmethod
    def _spaced_digits(value: object) -> str:
        """Formatiert eine DMR-Zielnummer für natürliche Einzelziffern-Ausgabe."""
        return " ".join(character for character in str(value) if character.isdigit())

    def _format_talkgroup_for_speech(self) -> None:
        text = self.talkgroup_edit.text().strip()
        compact = text.replace(" ", "")
        if compact.isdigit():
            self.talkgroup_edit.setText(self._spaced_digits(compact))

    def _target(self) -> tuple[int, int, str]:
        text = self.talkgroup_edit.text().strip().replace(" ", "")
        if not text.isdigit() or int(text) <= 0:
            raise ValueError("Bitte eine gültige Talkgroup als Zahl eingeben.")
        return int(text), self._timeslot, self._call_type

    def _save_preferences(self) -> None:
        tg, ts, call_type = self._target()
        self.preferences_store.save(
            OperatingPreferences(
                tg,
                ts,
                call_type,
                False,
                self.preferences.screenreader_ptt_lead_in_seconds,
            )
        )
        self.preferences = self.preferences_store.load()

    def _refresh_channel_label(self) -> None:
        call_label = "Gruppe" if self._call_type == "group" else "Privat"
        self.channel_label.setText(f"TS{self._timeslot} · {call_label}")
        self.channel_label.setAccessibleName(
            f"Timeslot {self._timeslot}, {call_label}ruf"
        )

    def _toggle_timeslot(self) -> None:
        if not self.controller.snapshot().can_edit_parameters:
            self.accessibility.announcer.announce(
                self.status_label,
                "Timeslot kann nur im getrennten Zustand geändert werden.",
                channel="easy-parameter-locked",
            )
            return
        self._timeslot = 1 if self._timeslot == 2 else 2
        self._refresh_channel_label()
        self.accessibility.announce_timeslot(self.status_label, self._timeslot)

    def _toggle_call_type(self) -> None:
        if not self.controller.snapshot().can_edit_parameters:
            self.accessibility.announcer.announce(
                self.status_label,
                "Rufart kann nur im getrennten Zustand geändert werden.",
                channel="easy-parameter-locked",
            )
            return
        self._call_type = "private" if self._call_type == "group" else "group"
        self._refresh_channel_label()
        self.accessibility.announce_call_type(self.status_label, self._call_type)

    def _announce_status(self) -> None:
        try:
            talkgroup, timeslot, call_type = self._target()
        except ValueError:
            talkgroup = self.preferences.talkgroup
            timeslot = self._timeslot
            call_type = self._call_type
        state = self.controller.snapshot().state
        labels = {
            RadioState.DISCONNECTED: "getrennt",
            RadioState.CONNECTING: "Verbindung wird hergestellt",
            RadioState.CONNECTED: "Empfang",
            RadioState.TRANSMITTING: "Senden",
            RadioState.DISCONNECTING: "Verbindung wird getrennt",
            RadioState.ERROR: "Fehler",
        }
        self.accessibility.announce_operation_context(
            self.status_label,
            talkgroup=talkgroup,
            timeslot=timeslot,
            call_type=call_type,
            state_label=labels[state],
        )

    def _toggle_connection(self) -> None:
        state = self.controller.snapshot().state
        if state in {RadioState.CONNECTED, RadioState.TRANSMITTING}:
            self._disconnect()
        elif state in {RadioState.DISCONNECTED, RadioState.ERROR}:
            self._connect()

    def _connect(self) -> None:
        try:
            talkgroup, timeslot, call_type = self._target()
            self._save_preferences()
        except Exception as error:
            QMessageBox.warning(self, "CarenDMR Easy", str(error))
            self._focus_talkgroup()
            return

        self._connect_requested = True
        self.status_label.setText("Verbindung wird hergestellt …")
        self._apply_radio_state(RadioState.CONNECTING)

        def worker() -> None:
            try:
                self.controller.connect(talkgroup, timeslot, call_type)
                self._updates.put(("connect_result", True))
            except Exception as error:
                self._updates.put(("connect_error", error))

        Thread(target=worker, name="CarenDMR-Easy-Connect", daemon=True).start()

    def _disconnect(self) -> None:
        if self._tx_active:
            self._stop_tx()
        self.status_label.setText("Verbindung wird getrennt …")

        def worker() -> None:
            try:
                completed = self.controller.disconnect(wait_timeout=8.0)
                if not completed:
                    raise RuntimeError("Die Verbindung konnte nicht rechtzeitig beendet werden.")
                self._updates.put(("disconnect_result", True))
            except Exception as error:
                self._updates.put(("disconnect_error", error))

        Thread(target=worker, name="CarenDMR-Easy-Disconnect", daemon=True).start()

    def _toggle_tx(self) -> None:
        if self._tx_stopping:
            return
        if self._tx_pending:
            self._cancel_pending_tx()
        elif self._tx_active:
            self._stop_tx()
        else:
            self._start_tx()

    def _start_tx(self) -> None:
        if self.controller.snapshot().state is not RadioState.CONNECTED:
            self.accessibility.announcer.announce(
                self.ptt_button,
                "PTT ist nur bei aktiver Verbindung möglich.",
                channel="easy-ptt-error",
            )
            return
        if not self._encoder_ready:
            self.accessibility.announcer.announce(
                self.ptt_button,
                "AMBE-Encoder ist noch nicht bereit.",
                channel="easy-ptt-error",
            )
            return

        self._tx_pending = True
        self.status_label.setText("TX wird vorbereitet")
        self.ptt_button.setText("PTT")
        self.ptt_button.setAccessibleName("PTT")
        self.accessibility.announcer.announce(
            self.ptt_button, "Senden.", channel="easy-tx-start", force=True
        )
        delay_ms = int(round(self.preferences.screenreader_ptt_lead_in_seconds * 1000))
        QTimer.singleShot(delay_ms, self._play_tx_start_cue if delay_ms > 0 else self._begin_tx)

    def _cancel_pending_tx(self) -> None:
        self._tx_pending = False
        self.status_label.setText("Empfang")
        self.ptt_button.setText("PTT")
        self.ptt_button.setAccessibleName("PTT")

    def _play_tx_start_cue(self) -> None:
        if not self._tx_pending or self.controller.snapshot().state is not RadioState.CONNECTED:
            return

        def worker() -> None:
            try:
                self.audio_cues.play_tx_start()
                self._updates.put(("tx_start_cue_done", None))
            except Exception as error:
                self._updates.put(("tx_start_cue_error", error))

        Thread(target=worker, name="CarenDMR-Easy-TX-Cue", daemon=True).start()

    def _begin_tx(self) -> None:
        if not self._tx_pending or self.controller.snapshot().state is not RadioState.CONNECTED:
            return
        self._tx_pending = False
        self._tx_active = True
        self._tx_stopping = False
        self._tx_stop_event = Event()
        self.status_label.setText("TX")
        self.ptt_button.setText("PTT")
        self.ptt_button.setAccessibleName("PTT")
        stop_event = self._tx_stop_event

        def worker() -> None:
            try:
                result = self.controller.ptt(
                    stop_event,
                    optimize=True,
                    tx_complete_callback=self._tx_wire_complete,
                )
                self._updates.put(("tx_result", result))
            except Exception as error:
                self._updates.put(("tx_error", error))

        Thread(target=worker, name="CarenDMR-Easy-TX", daemon=True).start()

    def _stop_tx(self) -> None:
        if not self._tx_active:
            return
        if self._tx_stop_event is not None:
            self._tx_stop_event.set()
        self._tx_stopping = True
        self.status_label.setText("TX wird beendet")
        self.ptt_button.setText("PTT")
        self.ptt_button.setAccessibleName("PTT")

    def _tx_wire_complete(self) -> None:
        """Quittiert das echte TX-Ende sofort, bevor RX das Audiogerät wieder übernimmt."""
        self._play_tx_stop_cue()

    def _play_tx_stop_cue(self) -> None:
        def worker() -> None:
            try:
                self.audio_cues.play_tx_stop()
            except Exception as error:
                # Der Funkpfad darf durch einen lokalen Quittungston niemals scheitern.
                # Für die Diagnose bleibt ein Fehler aber sichtbar.
                print(f"[EASY][AUDIO-CUE] TX-Endton fehlgeschlagen: {error}", file=sys.stderr)

        Thread(target=worker, name="CarenDMR-Easy-TX-End-Cue", daemon=True).start()

    def _finish_tx(self, error: Exception | None = None) -> None:
        self._tx_active = False
        self._tx_stopping = False
        self._tx_pending = False
        self._tx_stop_event = None
        self.ptt_button.setText("PTT")
        self.ptt_button.setAccessibleName("PTT")
        if error is not None:
            self.status_label.setText("Sendefehler")
            self.accessibility.announcer.announce(
                self.status_label,
                f"Sendefehler. {error}",
                channel="easy-tx-error",
                force=True,
            )
        self._apply_radio_state(self.controller.snapshot().state)
        if not self.ptt_button.hasFocus():
            self._focus_ptt()

    def _verify_encoder(self) -> None:
        def worker() -> None:
            try:
                self.encoder_service.verify_configured()
                self._updates.put(("encoder_ready", True))
            except Exception as error:
                self._updates.put(("encoder_error", error))

        Thread(target=worker, name="CarenDMR-Easy-Encoder", daemon=True).start()

    def _process_updates(self) -> None:
        try:
            while True:
                kind, value = self._updates.get_nowait()
                if kind == "radio_state":
                    self._apply_radio_state(value)
                elif kind == "connect_result":
                    # Der reale Zustand kommt über OperatingController/StateStore.
                    pass
                elif kind == "connect_error":
                    self._connect_requested = False
                    self.status_label.setText("Verbindungsfehler")
                    self.accessibility.announce_radio_state(
                        self.status_label, "ERROR", force=True
                    )
                    QMessageBox.critical(
                        self,
                        "CarenDMR Easy",
                        f"Verbindung fehlgeschlagen:\n\n{value}",
                    )
                elif kind == "disconnect_result":
                    pass
                elif kind == "disconnect_error":
                    self.status_label.setText("Fehler beim Trennen")
                    self.accessibility.announcer.announce(
                        self.status_label,
                        f"Trennen fehlgeschlagen. {value}",
                        channel="easy-disconnect-error",
                        force=True,
                    )
                elif kind == "encoder_ready":
                    self._encoder_ready = True
                    self._apply_radio_state(self.controller.snapshot().state)
                elif kind == "encoder_error":
                    self._encoder_ready = False
                    self._apply_radio_state(self.controller.snapshot().state)
                elif kind == "tx_start_cue_done":
                    QTimer.singleShot(120, self._begin_tx)
                elif kind == "tx_start_cue_error":
                    QTimer.singleShot(0, self._begin_tx)
                elif kind == "tx_result":
                    self._finish_tx()
                elif kind == "tx_error":
                    self._finish_tx(value)
        except queue.Empty:
            pass

    def _apply_radio_state(self, state: RadioState) -> None:
        state = RadioState(state)
        previous = self._last_radio_state
        self._last_radio_state = state

        editable = state in {RadioState.DISCONNECTED, RadioState.ERROR}
        self.talkgroup_edit.setEnabled(editable)
        self.connect_button.setEnabled(state is not RadioState.TRANSMITTING)
        self.ptt_button.setEnabled(
            state in {RadioState.CONNECTED, RadioState.TRANSMITTING}
            and self._encoder_ready
        )
        # Beenden bleibt in jedem Funkzustand verfügbar.
        self.exit_button.setEnabled(True)

        if state is RadioState.DISCONNECTED:
            self.status_label.setText("Getrennt")
            self.connect_button.setText("Verbinden")
                # Beim Aufbau kann der ReceiveService kurz seinen bisherigen Zustand
            # DISCONNECTED melden. Das ist technisch korrekt, für den Anwender aber
            # irreführend und darf nicht gesprochen werden.
            if previous is not RadioState.DISCONNECTED and not self._connect_requested:
                self.accessibility.announce_radio_state(self.status_label, "DISCONNECTED")
                QTimer.singleShot(0, self._focus_talkgroup)
        elif state is RadioState.CONNECTING:
            self.status_label.setText("Verbindung wird hergestellt …")
            self.connect_button.setText("Verbindung wird hergestellt")
            self.connect_button.setAccessibleName("Verbindung wird hergestellt")
        elif state is RadioState.CONNECTED:
            self._connect_requested = False
            self.status_label.setText("Empfang")
            self.connect_button.setText("Trennen")
            self.connect_button.setAccessibleName("Trennen")
            if previous not in {RadioState.CONNECTED, RadioState.TRANSMITTING}:
                self.accessibility.announce_radio_state(self.status_label, "CONNECTED")
                QTimer.singleShot(0, self._focus_ptt)
        elif state is RadioState.TRANSMITTING:
            self.status_label.setText("TX")
            self.connect_button.setText("Trennen")
            self.connect_button.setAccessibleName("Trennen")
        elif state is RadioState.DISCONNECTING:
            self.status_label.setText("Verbindung wird getrennt …")
            self.connect_button.setText("Verbindung wird getrennt")
            self.connect_button.setAccessibleName("Verbindung wird getrennt")
        else:
            self._connect_requested = False
            self.status_label.setText("Verbindungsfehler")
            self.connect_button.setText("Verbinden")
            self.connect_button.setAccessibleName("Verbinden")
            if previous is not RadioState.ERROR:
                self.accessibility.announce_radio_state(self.status_label, "ERROR")

    def _exit_application(self) -> None:
        """Beendet Easy jederzeit und stößt vorher ein sauberes Funkende an."""
        self.status_label.setText("CarenDMR wird beendet …")
        self.accessibility.announcer.announce(
            self.status_label,
            "CarenDMR wird beendet.",
            channel="easy-exit",
            force=True,
        )
        self._tx_pending = False
        if self._tx_stop_event is not None:
            self._tx_stop_event.set()
        self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Schließt Easy immer; aktive Funkstrecken werden vorher best-effort getrennt."""
        self._timer.stop()
        self._tx_pending = False
        if self._tx_stop_event is not None:
            self._tx_stop_event.set()
        try:
            self.controller.disconnect(wait_timeout=3.0)
        except Exception:
            # Fehler beim Trennen dürfen das Programmende niemals verhindern.
            pass
        event.accept()


def run_easy_gui(project_root: Path) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    apply_theme(app, suppress_native_focus=False)
    from carendmr.bootstrap import build_first_run_services
    from carendmr.ui_qt.first_run_dialogs import run_first_run_setup
    run_first_run_setup(build_first_run_services(project_root))
    window = EasyWindow(project_root)
    window.show()
    return int(app.exec())
