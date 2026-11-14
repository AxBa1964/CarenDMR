"""Funktionaler Qt-Betrieb für CarenDMR 0.0.26.0.

Diese Stufe portiert ausschließlich den stabilen Funkbetrieb. Es gibt bewusst
keine eigene TTS- oder Screenreader-Sonderlogik.
"""
from __future__ import annotations

import base64
import json
import queue
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from threading import Event, Thread

from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtGui import QAction, QAccessible, QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QAbstractButton, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QComboBox,
    QStatusBar, QTabWidget, QVBoxLayout, QWidget, QSlider, QCheckBox, QGridLayout,
    QFrame, QSizePolicy, QDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView,
)

from carendmr.application import RadioState
from carendmr.application.diagnostics_service import start_timing_log, timing_mark
from carendmr.bootstrap import DesktopServices, RadioCore, build_desktop_services, build_radio_core
from carendmr.application.operating_preferences import OperatingPreferences, OperatingPreferencesStore
from carendmr.domain import ApplicationState, ConnectionState, DmrChannel
from carendmr.version import __version__
from carendmr.ui_qt.theme import METRICS
from carendmr.accessibility.hotkeys import DEFAULT_HOTKEYS
from carendmr.ui_qt.settings_dialog import SettingsDialog
from carendmr.ui_qt.history_widget import QsoHistoryWidget
from carendmr.ui_qt.theme import apply_theme
from carendmr.ui_qt.accessibility_manager import AccessibilityManager
from carendmr.ui_qt.audio_cue import AudioCuePlayer
from carendmr.ui_qt.operating_indicators import LevelMeter, StatusIndicator
from carendmr.ui_qt.talkgroup_search_widget import TalkgroupSearchWidget
from carendmr.ui_qt.favorites_widget import FavoritesWidget
from carendmr.ui_qt.audio_tool_windows import AudioBenchmarkWindow, AudioCoachWindow, AudioLabWindow
from carendmr.audio import AudioDirection, TxAudioTunerSettings, TUNER_PRESETS
from carendmr.ipc.channel_control import CarenDMRChannelServer
from carendmr.qrz import QrzNotFound, QrzServiceError, QrzLogbookError
from carendmr.adif_udp import AdifUdpError
from carendmr.ui_qt.qrz_window import QrzStationWindow
from carendmr.ui_qt.window_geometry import WindowGeometryManager
from carendmr.ui_qt.main_window_logbook import MainWindowLogbookMixin
from carendmr.ui_qt.main_window_windows import MainWindowWindowsMixin
from carendmr.ui_qt.main_window_audio import MainWindowAudioMixin
from carendmr.ui_qt.main_window_channels import MainWindowChannelsMixin
from carendmr.ui_qt.main_window_radio import MainWindowRadioMixin
from carendmr.tg_monitor.instance_control import is_tg_monitor_running, send_tg_monitor_command


class MainWindow(
    QMainWindow,
    MainWindowLogbookMixin,
    MainWindowWindowsMixin,
    MainWindowAudioMixin,
    MainWindowChannelsMixin,
    MainWindowRadioMixin,
):
    def __init__(
        self,
        project_root: Path,
        core: RadioCore | None = None,
        services: DesktopServices | None = None,
    ) -> None:
        super().__init__()
        self.project_root = Path(project_root)
        timing_log = start_timing_log(self.project_root)
        timing_mark("PROGRAMMSTART_QT", f"Version {__version__}; Log={timing_log}")
        self.setWindowTitle(f"CarenDMR {__version__} – Funkgerät auf dem Desktop")
        self.resize(980, 720)

        # Funkkern (Empfang, Audio, Encoder, Parrot, ConnectionManager) kommt
        # aus dem gemeinsamen Startpunkt und ist identisch zur Easy-Oberfläche.
        self.radio_core = core or build_radio_core(self.project_root)
        self.events = self.radio_core.events
        self.receive_service = self.radio_core.receive_service
        self.encoder_service = self.radio_core.encoder_service
        self.audio_send_service = self.radio_core.audio_send_service
        self.parrot_service = self.radio_core.parrot_service
        self.connection_manager = self.radio_core.connection_manager
        # Ab 0.2.1.86 laufen Verbinden, Trennen und Senden über den
        # OperatingController. Seine Zustandsmaschine ist die einzige Quelle
        # für den Bedienzustand – identisch zur Easy-Oberfläche.
        self.controller = self.radio_core.controller
        # build_radio_core() hat die RX-AGC bereits diagnosehalber ausgeschaltet.
        timing_mark("RX_AGC_DIAGNOSE", "Beim Programmstart ausgeschaltet")
        self.preferences_store = OperatingPreferencesStore(self.project_root / "config" / "operating.local.json")
        self.preferences = self.preferences_store.load()
        self._selected_timeslot = self.preferences.timeslot
        self._selected_call_type = self.preferences.call_type
        # Zusatzdienste (QRZ, Logbuch, ADIF, Favoriten, Hotkeys, Benchmark …)
        # kommen ebenfalls aus dem gemeinsamen Startpunkt.
        self.services = services or build_desktop_services(self.radio_core)
        self.station_settings = self.services.station_settings
        self.local_audio_lab_service = self.services.local_audio_lab
        self.qso_recording_service = self.services.qso_recording
        self.radio_state = self.controller.radio_state
        self._updates: queue.SimpleQueue[tuple[str, object]] = queue.SimpleQueue()
        self._tx_stop_event: Event | None = None
        self._tx_active = False
        self._tx_stopping = False
        self._tx_pending = False
        self._tx_elapsed_seconds = 0
        self._tx_warning_played = False
        self._rx_level = 0.0
        self._mic_level = 0.0
        self._encoder_ready = False
        self._settings_dialog: SettingsDialog | None = None
        self._audio_benchmark_window: AudioBenchmarkWindow | None = None
        self._audio_coach_window: AudioCoachWindow | None = None
        self._audio_lab_window: AudioLabWindow | None = None
        self._audio_tuner_dialog: QDialog | None = None
        self._qrz_window: QrzStationWindow | None = None
        self._qrz_profile = None
        self._qrz_own_profile = None
        self._qrz_lookup_callsign = ""
        self._qrz_lookup_pending = False
        self.qrz_service = self.services.qrz_lookup
        self.qrz_logbook_service = self.services.qrz_logbook
        self._qrz_log_pending = False
        self.adif_udp_service = self.services.adif_udp
        self._recent_station_signature: tuple[int, ...] = ()
        self.hotkey_manager = self.services.hotkeys
        self.favorite_service = self.services.favorites
        self.talkgroup_search_service = self.services.talkgroup_search
        self.talkgroup_catalog_service = self.services.talkgroup_catalog
        self.audio_benchmark_service = self.services.audio_benchmark
        self.receive_service.set_call_activity_observer(self._benchmark_call_activity)
        self.receive_service.set_decoded_pcm_callback(self._benchmark_pcm)
        self.receive_service.set_connection_callbacks(
            lost=lambda: self._updates.put(("benchmark_connection_lost", None)),
            restored=self.audio_benchmark_service.connection_restored,
        )
        self._current_dmr_channel: DmrChannel | None = None
        self._shortcuts: list[QShortcut] = []
        self.accessibility = AccessibilityManager()
        self.audio_cues = AudioCuePlayer(self.audio_send_service)
        self._last_focus_radio_state: RadioState = RadioState.DISCONNECTED
        self._startup_announcement_timer = QTimer(self)
        self._startup_announcement_timer.setSingleShot(True)
        self._startup_announcement_timer.timeout.connect(self.announce_operation_context)
        self._connected_announcement_pending = False
        self._pending_hot_favorite = None
        self._pending_external_channel = None
        self._tx_elapsed_timer = QTimer(self)
        self._tx_elapsed_timer.setInterval(1000)
        self._tx_elapsed_timer.timeout.connect(self._increment_tx_elapsed)
        self.window_geometry = WindowGeometryManager(self.project_root, self)

        self._build_ui()
        self._restore_window_geometry()
        self._restore_saved_dmr_channel()
        QApplication.instance().installEventFilter(self)
        self._bind_shortcuts()
        self.receive_service.state_store.subscribe(lambda state: self._updates.put(("state", state)))
        self.receive_service.history.subscribe_added(lambda entry: self._updates.put(("history_added", entry)))
        self.receive_service.set_output_level_callback(lambda level: self._updates.put(("rx_level", level)))
        self.events.subscribe(lambda event: self._updates.put(("event", event)))

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._process_updates)
        self._timer.start(100)
        QTimer.singleShot(0, self._verify_encoder)
        self._apply_state(self.receive_service.state_store.get())
        self._channel_control_server = CarenDMRChannelServer(self._handle_external_channel_request)
        if not self._channel_control_server.start():
            self.statusBar().showMessage("Lokale TG-Monitor-Übergabe konnte nicht gestartet werden.", 5000)

    def _build_ui(self) -> None:
        """Baut das Layout V1, ohne die vorhandene Bedienlogik zu verändern."""
        self.tabs = QTabWidget(self)
        self.tabs.setObjectName("mainTabs")
        operation_page = QWidget(self.tabs)
        operation_page.setObjectName("operationPage")
        root = QVBoxLayout(operation_page)
        root.setContentsMargins(12, 8, 12, 8)
        root.setSpacing(8)

        # Kompakter Verbindungsstatus. App-Name/Untertitel stehen bereits in
        # der Fenstertitelleiste und verbrauchen im Funkbetrieb keine Extra-Höhe.
        status_row = QHBoxLayout()
        status_row.addStretch(1)
        self.connection_indicator = StatusIndicator(operation_page)
        self.connection_label = self.connection_indicator
        self.server_label = QLabel("Message Server: nicht verbunden")
        self.server_label.setObjectName("secondaryText")
        status_row.addWidget(self.connection_indicator)
        status_row.addWidget(self.server_label)
        root.addLayout(status_row)

        content = QGridLayout()
        content.setHorizontalSpacing(12)
        content.setVerticalSpacing(8)
        content.setColumnStretch(0, 3)
        content.setColumnStretch(1, 2)
        root.addLayout(content)

        # DMR-Kanal und Verbindung.
        target_card = QFrame(operation_page)
        target_card.setObjectName("card")
        target_layout = QGridLayout(target_card)
        target_layout.setContentsMargins(14, 9, 14, 9)
        target_layout.setHorizontalSpacing(12)
        target_layout.setVerticalSpacing(5)
        target_heading = QLabel("DMR-KANAL")
        target_heading.setObjectName("sectionTitle")
        target_layout.addWidget(target_heading, 0, 0, 1, 6)
        current_caption = QLabel("AKTUELLER KANAL")
        current_caption.setObjectName("fieldCaption")
        self.current_tg_label = QLabel(str(self.preferences.talkgroup))
        self.current_tg_label.setObjectName("currentTalkgroup")
        self.current_tg_name_label = QLabel("")
        self.current_tg_name_label.setObjectName("secondaryText")
        self.current_tg_name_label.setAccessibleName("Name der aktuellen Talkgroup")
        self.current_tg_name_label.setAccessibleDescription("Name des aktuell gewählten DMR-Kanals")
        self.current_channel_meta_label = QLabel("")
        self.current_channel_meta_label.setObjectName("channelMeta")
        current_column = QVBoxLayout()
        current_column.setSpacing(0)
        current_column.addWidget(current_caption)
        current_column.addWidget(self.current_tg_label)
        current_column.addWidget(self.current_tg_name_label)
        current_column.addWidget(self.current_channel_meta_label)
        target_layout.addLayout(current_column, 1, 0, 3, 1)

        # Schnellwahl: drei feste Favoriten plus Zugriff auf die komplette Favoritenliste.
        self.favorite_hot_buttons = []
        hot_row = QHBoxLayout()
        hot_row.setSpacing(6)
        for index in range(3):
            button = QPushButton("–")
            button.setObjectName("favoriteHotButton")
            button.setMinimumHeight(34)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            button.clicked.connect(lambda _checked=False, slot=index: self._activate_hot_favorite(slot))
            hot_row.addWidget(button, 1)
            self.favorite_hot_buttons.append(button)

        self.favorite_combo = QComboBox(target_card)
        self.favorite_combo.setObjectName("favoriteCombo")
        self.favorite_combo.setAccessibleName("Alle Favoriten")
        self.favorite_combo.setToolTip("Einen gespeicherten Favoriten auswählen und vollständig übernehmen")
        self.favorite_combo.setMinimumHeight(34)
        self.favorite_combo.setMinimumWidth(170)
        self.favorite_combo.currentIndexChanged.connect(self._favorite_combo_selected)
        hot_row.addWidget(self.favorite_combo, 1)
        target_layout.addLayout(hot_row, 1, 1, 1, 5)

        # Manuelle Kanalwahl als geschlossene Bedienzeile.
        self.favorite_button = QPushButton("☆")
        self.favorite_button.setObjectName("favoriteButton")
        self.favorite_button.setAccessibleName("Aktuellen DMR-Kanal als Favorit speichern")
        self.favorite_button.setToolTip("Aktuellen DMR-Kanal als Favorit speichern oder bearbeiten")
        self.favorite_button.setFixedSize(34, 32)
        self.favorite_button.clicked.connect(self._edit_current_favorite)

        self.tg_edit = TalkgroupSearchWidget(self.talkgroup_search_service, target_card)
        self.tg_edit.setObjectName("talkgroupInput")
        self.tg_edit.setPlaceholderText("Talkgroup nach Nummer oder Name suchen")
        self.tg_edit.setMaxLength(64)
        self.tg_edit.setAccessibleName("Talkgroup")
        self.tg_edit.setAccessibleDescription("Nach Nummer oder Name suchen")
        self.tg_edit.channel_selected.connect(self._apply_selected_channel)

        self.ts1_radio = QPushButton("TS1")
        self.ts2_radio = QPushButton("TS2")
        self.ts1_radio.setObjectName("segmentButton")
        self.ts2_radio.setObjectName("segmentButton")
        for button in (self.ts1_radio, self.ts2_radio):
            button.setFixedSize(48, 32)
            button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.ts1_radio.clicked.connect(lambda: self._select_timeslot(1))
        self.ts2_radio.clicked.connect(lambda: self._select_timeslot(2))

        self.group_radio = QPushButton("Gruppe")
        self.private_radio = QPushButton("Privat")
        self.group_radio.setObjectName("segmentButton")
        self.private_radio.setObjectName("segmentButton")
        for button in (self.group_radio, self.private_radio):
            button.setFixedHeight(32)
            button.setMinimumWidth(66)
            button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.group_radio.clicked.connect(lambda: self._select_call_type("group"))
        self.private_radio.clicked.connect(lambda: self._select_call_type("private"))

        manual_row = QHBoxLayout()
        manual_row.setSpacing(6)
        manual_row.addWidget(self.favorite_button)
        manual_row.addWidget(self.tg_edit, 1)
        manual_row.addWidget(self.ts1_radio)
        manual_row.addWidget(self.ts2_radio)
        manual_row.addWidget(self.group_radio)
        manual_row.addWidget(self.private_radio)
        target_layout.addLayout(manual_row, 2, 1, 1, 4)

        hint_row = QHBoxLayout()
        hint_row.setSpacing(12)
        self.timeslot_caption = QLabel("Timeslot  [Ctrl+T]")
        self.timeslot_caption.setObjectName("compactHint")
        self.calltype_caption = QLabel("Rufart  [Ctrl+R]")
        self.calltype_caption.setObjectName("compactHint")
        hint_row.addStretch(1)
        hint_row.addWidget(self.timeslot_caption)
        hint_row.addWidget(self.calltype_caption)
        target_layout.addLayout(hint_row, 3, 1, 1, 4)

        self.connect_button = QPushButton("Verbinden")
        self.connect_button.setObjectName("connectButton")
        self.connect_button.setFixedSize(METRICS.connection_control_width, 66)
        self.connect_button.clicked.connect(self._toggle_connection)
        target_layout.addWidget(self.connect_button, 2, 5, 2, 1)
        self._sync_radio_controls()
        self._update_radio_hotkey_hints()
        content.addWidget(target_card, 0, 0, 1, 2)

        # Aktuelle Station: klare Wertefelder + echte Tabelle für die letzten Stationen.
        station_card = QFrame(operation_page)
        station_card.setObjectName("card")
        station_layout = QGridLayout(station_card)
        station_layout.setContentsMargins(14, 10, 14, 10)
        station_layout.setHorizontalSpacing(12)
        station_layout.setVerticalSpacing(7)

        station_heading = QLabel("AKTUELLE STATION")
        station_heading.setObjectName("sectionTitle")
        station_layout.addWidget(station_heading, 0, 0, 1, 2)

        # Der Button selbst behält seinen Platz auch unsichtbar. So gibt es
        # weder Layout-Sprung noch einen sichtbaren Platzhalter-Hintergrund.
        self.qrz_button = QPushButton("QRZ.com", station_card)
        self.qrz_button.setObjectName("qrzCompactButton")
        self.qrz_button.setAccessibleName("QRZ.com Stationsinformationen")
        self.qrz_button.setToolTip("Zusätzliche Stationsinformationen von QRZ.com anzeigen")
        self.qrz_button.setFixedSize(108, 30)
        qrz_size_policy = self.qrz_button.sizePolicy()
        qrz_size_policy.setRetainSizeWhenHidden(True)
        self.qrz_button.setSizePolicy(qrz_size_policy)
        self.qrz_button.clicked.connect(self._open_qrz_station)
        self.qrz_button.setVisible(False)
        station_layout.addWidget(
            self.qrz_button, 0, 2, 1, 1,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )
        station_layout.setColumnStretch(3, 1)

        self.callsign_label = QLabel("Nicht bekannt")
        self.callsign_label.setObjectName("callsignDisplay")
        self.name_label = QLabel("Nicht bekannt")
        self.name_label.setObjectName("stationName")
        station_layout.addWidget(self.callsign_label, 1, 0, 1, 2)
        station_layout.addWidget(self.name_label, 1, 2, 1, 2)

        self.location_label = QLabel("Nicht bekannt")
        self.country_label = QLabel("Nicht bekannt")
        self.dmr_id_label = QLabel("Kein aktiver Sprecher")
        self.target_label = QLabel("–")
        self.duration_label = QLabel("0 Sekunden")
        self.qso_status_label = QLabel("Keine Station aktiv")
        self.qso_status_label.setObjectName("qsoStatus")

        detail_labels = (
            ("Ort / Region", self.location_label),
            ("Land", self.country_label),
            ("DMR-ID", self.dmr_id_label),
            ("Sprechdauer", self.duration_label),
            ("QSO-Status", self.qso_status_label),
        )
        detail_positions = (
            ("Ort / Region", self.location_label, 2, 0),
            ("Land", self.country_label, 2, 2),
            ("DMR-ID", self.dmr_id_label, 3, 0),
            ("Sprechdauer", self.duration_label, 3, 2),
            ("QSO-Status", self.qso_status_label, 4, 0),
        )
        for caption, value, row, column in detail_positions:
            cap = QLabel(caption)
            cap.setObjectName("fieldCaption")
            value.setObjectName("fieldValue" if value is not self.qso_status_label else "qsoStatusValue")
            value.setMinimumHeight(30)
            value.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            station_layout.addWidget(cap, row, column)
            if value is self.qso_status_label:
                station_layout.addWidget(value, row, column + 1, 1, 2)
            else:
                station_layout.addWidget(value, row, column + 1)

        self.qso_mark_button = QPushButton("Als QSO markieren", station_card)
        self.qso_mark_button.setAccessibleName("Aktuelle Station als QSO gesprochen markieren")
        self.qso_mark_button.setEnabled(False)
        self.qso_mark_button.clicked.connect(self._mark_current_station_worked)
        station_layout.addWidget(self.qso_mark_button, 4, 3)

        recent_heading = QLabel("ZULETZT GEHÖRT")
        recent_heading.setObjectName("sectionTitle")
        station_layout.addWidget(recent_heading, 5, 0, 1, 4)

        self.recent_station_table = QTableWidget(0, 5, station_card)
        self.recent_station_table.setObjectName("recentStations")
        self.recent_station_table.setHorizontalHeaderLabels(
            ["Zeit", "Rufzeichen", "Name", "Land", "Letztes QSO"]
        )
        self.recent_station_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.recent_station_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.recent_station_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.recent_station_table.setAlternatingRowColors(True)
        self.recent_station_table.verticalHeader().setVisible(False)
        self.recent_station_table.setShowGrid(True)
        self.recent_station_table.setMinimumHeight(130)
        self.recent_station_table.setMaximumHeight(130)
        recent_header = self.recent_station_table.horizontalHeader()
        recent_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        recent_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        recent_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        recent_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        recent_header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        station_layout.addWidget(self.recent_station_table, 6, 0, 1, 4)

        self._refresh_recent_stations(force=True)
        station_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        content.addWidget(station_card, 1, 0)
        # Rechte Bedienkarte: tägliche Audiofunktionen und PTT, ohne neue Controls.
        control_card = QFrame(operation_page)
        control_card.setObjectName("card")
        control_layout = QVBoxLayout(control_card)
        control_layout.setContentsMargins(2, 10, 2, 10)
        control_layout.setSpacing(6)
        control_heading = QLabel("FUNK- UND AUDIOBEDIENUNG")
        control_heading.setObjectName("sectionTitle")
        control_layout.addWidget(control_heading)

        self.operation_gain_slider = QSlider(Qt.Orientation.Horizontal)
        self.operation_gain_slider.setRange(0, 100)
        self.operation_gain_slider.setAccessibleName("TX-Pegel")
        self.operation_gain_slider.setAccessibleDescription("")
        self.operation_gain_value = QLabel("100 %")
        self.operation_gain_value.setObjectName("valueLabel")
        gain_row = QGridLayout()
        gain_caption = QLabel("TX-Pegel")
        gain_caption.setObjectName("fieldCaption")
        gain_row.addWidget(gain_caption, 0, 0)
        gain_row.addWidget(self.operation_gain_value, 0, 1, alignment=Qt.AlignmentFlag.AlignRight)
        gain_row.addWidget(self.operation_gain_slider, 1, 0, 1, 2)
        self.mic_level_meter = LevelMeter(control_card)
        mic_level_caption = QLabel("MIC-PEGEL")
        mic_level_caption.setObjectName("fieldCaption")
        gain_row.addWidget(mic_level_caption, 2, 0, 1, 2)
        gain_row.addWidget(self.mic_level_meter, 3, 0, 1, 2)
        control_layout.addLayout(gain_row)

        self.operation_volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.operation_volume_slider.setRange(0, 100)
        self.operation_volume_slider.setAccessibleName("RX-Lautstärke")
        self.operation_volume_slider.setAccessibleDescription("")
        self.operation_volume_value = QLabel("100 %")
        self.operation_volume_value.setObjectName("valueLabel")
        volume_row = QGridLayout()
        volume_caption = QLabel("RX-Lautstärke")
        volume_caption.setObjectName("fieldCaption")
        volume_row.addWidget(volume_caption, 0, 0)
        volume_row.addWidget(self.operation_volume_value, 0, 1, alignment=Qt.AlignmentFlag.AlignRight)
        volume_row.addWidget(self.operation_volume_slider, 1, 0, 1, 2)
        self.rx_level_meter = LevelMeter(control_card)
        rx_level_caption = QLabel("RX-PEGEL")
        rx_level_caption.setObjectName("fieldCaption")
        volume_row.addWidget(rx_level_caption, 2, 0, 1, 2)
        volume_row.addWidget(self.rx_level_meter, 3, 0, 1, 2)
        control_layout.addLayout(volume_row)

        checks = QHBoxLayout()
        self.operation_muted_check = QCheckBox("Empfang stumm")
        self.operation_agc_check = QCheckBox("AGC aktiv")
        checks.addWidget(self.operation_muted_check)
        checks.addWidget(self.operation_agc_check)
        checks.addStretch(1)
        control_layout.addLayout(checks)

        # Audio-Tuner in eigenem Fenster: Die Betriebsmaske bleibt beim
        # Öffnen/Schließen vollständig stabil und verschiebt keine Bedienelemente.
        self.audio_tuner_button = QPushButton("Audio-Tuner…")
        self.audio_tuner_button.setAccessibleName("DMR Audio-Tuner öffnen")
        control_layout.addWidget(self.audio_tuner_button)
        self._build_audio_tuner_dialog()

        self.record_button = QPushButton("Mitschnitt starten")
        self.record_button.setAccessibleName("QSO-Mitschnitt starten")
        self.record_button.clicked.connect(self._toggle_qso_recording)
        control_layout.addWidget(self.record_button)

        self.ptt_button = QPushButton("TX")
        self.ptt_button.setObjectName("pttButton")
        self.ptt_button.setMinimumHeight(150)
        self.ptt_button.setMaximumHeight(150)
        self.ptt_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.ptt_button.clicked.connect(self._toggle_tx)
        self.tx_status = QLabel("RX")
        self.tx_status.setObjectName("txStatus")
        self.tx_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tx_status.hide()
        control_layout.addWidget(self.ptt_button)
        control_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        content.addWidget(control_card, 1, 1, alignment=Qt.AlignmentFlag.AlignTop)

        # Betriebsinformationen nur einmal und bewusst kompakt.
        info_card = QFrame(operation_page)
        info_card.setObjectName("card")
        info_layout = QGridLayout(info_card)
        info_layout.setContentsMargins(14, 7, 14, 7)
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
        info_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        content.addWidget(info_card, 2, 0, 1, 2)
        root.addStretch(1)

        self.operation_gain_slider.valueChanged.connect(self._operation_gain_changed)
        self.operation_volume_slider.valueChanged.connect(self._operation_volume_changed)
        self.operation_muted_check.toggled.connect(self._operation_muted_changed)
        self.operation_agc_check.toggled.connect(self._operation_agc_changed)
        self.audio_tuner_button.clicked.connect(self._show_audio_tuner_dialog)
        self.audio_tuner_profile.currentTextChanged.connect(self._audio_tuner_profile_changed)
        for key, (slider, _label, _suffix) in self.audio_tuner_sliders.items():
            slider.valueChanged.connect(lambda _value, tuner_key=key: self._audio_tuner_slider_changed(tuner_key))
        self.audio_tuner_reset_button.clicked.connect(lambda: self._apply_audio_tuner_preset("Neutral"))
        self._sync_operation_audio_controls()

        operation_page.setAccessibleName("")
        operation_page.setAccessibleDescription("")
        self.tabs.tabBar().setAccessibleName("Hauptbereiche")
        self.tabs.addTab(operation_page, "Betrieb")
        self.history_widget = QsoHistoryWidget(
            self.receive_service.history,
            self._show_status,
            self._history_worked_changed,
            self._log_history_qso_to_qrz,
            self._history_qrz_status,
            self._send_history_qso_adif_udp,
            self._sync_qso_history,
            self.tabs,
            self.accessibility,
        )
        self.tabs.addTab(self.history_widget, "QSO-Historie")
        self.favorites_widget = FavoritesWidget(self.favorite_service, self.talkgroup_search_service, self.talkgroup_catalog_service, self.tabs)
        self.favorites_widget.channel_requested.connect(self._apply_favorite_channel)
        self.favorites_widget.changed.connect(self._refresh_favorites)
        self.tabs.addTab(self.favorites_widget, "Talkgroups")
        self._refresh_favorites()
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
        QWidget.setTabOrder(self.favorite_button, self.tg_edit)
        QWidget.setTabOrder(self.tg_edit, self.connect_button)
        QWidget.setTabOrder(self.connect_button, self.operation_gain_slider)
        QWidget.setTabOrder(self.operation_gain_slider, self.operation_volume_slider)
        QWidget.setTabOrder(self.operation_volume_slider, self.operation_muted_check)
        QWidget.setTabOrder(self.operation_muted_check, self.operation_agc_check)
        QWidget.setTabOrder(self.operation_agc_check, self.record_button)
        QWidget.setTabOrder(self.record_button, self.ptt_button)


    def _show_status(self, message: str) -> None:
        self.statusBar().showMessage(message)

    def _operation_context_text(self) -> str:
        tg, ts, call_type = self._target()
        call_label = "Privatruf" if call_type == "private" else "Gruppenruf"
        state = self.radio_state.state
        if state is RadioState.TRANSMITTING:
            state_label = "Senden aktiv"
        elif state is RadioState.CONNECTED:
            state_label = "Verbunden, Empfang aktiv"
        elif state is RadioState.CONNECTING:
            state_label = "Verbindung wird hergestellt"
        elif state is RadioState.DISCONNECTING:
            state_label = "Verbindung wird getrennt"
        else:
            state_label = "Getrennt"
        return f"Betrieb. Talkgroup {tg}. Timeslot {ts}. Rufart {call_label}. {state_label}."

    def announce_operation_context(self) -> None:
        """Meldet beim Start oder Betreten des Betriebs den aktuellen Kontext."""
        if self.tabs.currentIndex() != 0 or not self.isVisible():
            return
        tg, ts, call_type = self._target()
        state_label = self._operation_context_text().rsplit(". ", 1)[-1].rstrip(".")
        self.accessibility.announce_operation_context(
            self.connection_label,
            talkgroup=tg,
            timeslot=ts,
            call_type=call_type,
            state_label=state_label,
        )

    def _announce_radio_state(self, state: RadioState, *, force: bool = False) -> None:
        """Delegiert abgeschlossene Funkzustände zentral an den AccessibilityManager."""
        if state in {RadioState.CONNECTING, RadioState.DISCONNECTING}:
            return
        self.accessibility.announce_radio_state(
            self.connection_label, state.name, force=force
        )


    def _tab_changed(self, index: int) -> None:
        if index == 0:
            QTimer.singleShot(0, self.announce_operation_context)
        elif hasattr(self, "history_widget") and self.tabs.widget(index) is self.history_widget:
            self.history_widget.refresh()
            QTimer.singleShot(0, self.history_widget.announce_context)


    def _refresh_recent_stations(self, *, force: bool = False) -> None:
        if not hasattr(self, "recent_station_table"):
            return
        # Für den praktischen Funkbetrieb sind die letzten drei unterschiedlichen
        # Stationen nützlicher als drei einzelne Durchgänge derselben Station.
        entries = self.receive_service.history.list_recent(limit=20)
        unique = []
        seen_ids = set()
        for entry in entries:
            source_id = int(entry.source_id)
            if source_id in seen_ids:
                continue
            seen_ids.add(source_id)
            unique.append(entry)
            if len(unique) == 3:
                break

        signature = tuple(int(entry.id) for entry in unique)
        if not force and signature == self._recent_station_signature:
            return
        self._recent_station_signature = signature

        table = self.recent_station_table
        table.setRowCount(len(unique))
        for row, entry in enumerate(unique):
            try:
                stamp = datetime.fromisoformat(entry.ended_at).astimezone().strftime("%H:%M")
            except (TypeError, ValueError):
                stamp = "--:--"
            worked_at = self.receive_service.history.last_worked_at(entry.source_id)
            values = (
                stamp,
                entry.callsign or f"DMR-ID {entry.source_id}",
                entry.name or "–",
                entry.country or "–",
                self._format_qso_time(worked_at) if worked_at else "–",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column == 0:
                    item.setTextAlignment(int(Qt.AlignmentFlag.AlignCenter))
                table.setItem(row, column, item)
            table.setRowHeight(row, 30)


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

    def _update_radio_hotkey_hints(self) -> None:
        """Zeigt die aktuell konfigurierten Pflicht-Hotkeys direkt am DMR-Kanal."""
        mapping = self.hotkey_manager.mapping
        ts_key = mapping.get("TS_CHANGE") or DEFAULT_HOTKEYS["TS_CHANGE"]
        call_key = mapping.get("CALLTYPE_CHANGE") or DEFAULT_HOTKEYS["CALLTYPE_CHANGE"]
        if hasattr(self, "timeslot_caption"):
            self.timeslot_caption.setText(f"Timeslot  [{ts_key}]")
        if hasattr(self, "calltype_caption"):
            self.calltype_caption.setText(f"Rufart  [{call_key}]")

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
        self._update_radio_hotkey_hints()
        self.statusBar().showMessage("Hotkeys wurden übernommen.")

    def _focused_button(self) -> QAbstractButton | None:
        """Liefert das aktuell fokussierte Qt-Schaltelement, falls vorhanden."""
        widget = QApplication.focusWidget()
        return widget if isinstance(widget, QAbstractButton) else None

    def eventFilter(self, watched, event) -> bool:
        """Aktiviert fokussierte Buttons mit Enter, ohne Eingabefelder zu stören."""
        if event.type() == QEvent.Type.KeyPress and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            button = self._focused_button()
            if button is not None and button.isEnabled() and not button.property("radioFlag"):
                button.click()
                event.accept()
                return True
        return super().eventFilter(watched, event)

    def _activate_focused_button(self) -> None:
        """Kompatibilitätshelfer für Tests und gezielte Button-Aktivierung."""
        button = self._focused_button()
        if button is not None and button.isEnabled() and not button.property("radioFlag"):
            button.click()

    def _handle_space_shortcut(self) -> None:
        """Leertaste bedient fokussierte Buttons, sonst dient sie als PTT-Toggle."""
        button = self._focused_button()
        if button is not None:
            if button.property("radioFlag"):
                return
            if button.isEnabled():
                button.click()
            return
        self._toggle_tx()


        # Keine zusätzliche RX-Ansage; der fokussierte Button meldet nur TX.


    def _process_updates(self) -> None:
        try:
            while True:
                kind, value = self._updates.get_nowait()
                if kind == "state":
                    self._apply_state(value)
                elif kind == "history_added":
                    self._refresh_recent_stations(force=True)
                elif kind == "event":
                    self.last_event_label.setText(str(getattr(value, "message", value)))
                elif kind == "connect_result":
                    # Den Zustand (auch bei unverändertem Ziel) führt der Controller.
                    if bool(value):
                        self.statusBar().showMessage("Empfang wird gestartet …")
                    self._set_controls_for_state(self.radio_state.state)
                elif kind == "connect_error":
                    # Der Controller hat bereits auf ERROR gestellt.
                    self.connection_indicator.set_state("error")
                    self.statusBar().showMessage(f"Verbindungsfehler: {value}")
                    QMessageBox.critical(self, "CarenDMR", f"Verbindung fehlgeschlagen:\n\n{value}")
                    self._set_controls_for_state(self.radio_state.state)
                elif kind == "disconnect_result":
                    self.radio_state.synchronize(RadioState.DISCONNECTED)
                    self._set_controls_for_state(self.radio_state.state)
                    if self._pending_external_channel is not None:
                        channel = self._pending_external_channel
                        self.statusBar().showMessage("Verbindung getrennt; TG-Monitor-Kanal wird übernommen …")
                        QTimer.singleShot(0, lambda selected=channel: self._connect_external_channel(selected))
                    elif self._pending_hot_favorite is not None:
                        channel = self._pending_hot_favorite
                        self.statusBar().showMessage("Verbindung getrennt; Schnellwahl wird übernommen …")
                        QTimer.singleShot(0, lambda selected=channel: self._connect_hot_favorite(selected))
                    else:
                        self.statusBar().showMessage("Empfang und Verbindung beendet. Neue Talkgroup kann eingegeben werden.")
                        QTimer.singleShot(0, self._focus_talkgroup)
                elif kind == "disconnect_error":
                    self.radio_state.synchronize(RadioState.ERROR)
                    self.statusBar().showMessage(f"Trennen fehlgeschlagen: {value}")
                elif kind == "encoder_ready":
                    self._encoder_ready = True
                    self._set_controls_for_state(self.radio_state.state)
                elif kind == "encoder_error":
                    self._encoder_ready = False
                    self._set_controls_for_state(self.radio_state.state)
                elif kind == "rx_level":
                    self._rx_level = float(value)
                    self.rx_level_meter.set_level(self._rx_level)
                elif kind == "mic_level":
                    self._mic_level = float(value)
                    self.mic_level_meter.set_level(self._mic_level)
                elif kind == "qrz_result":
                    callsign, profile, own_profile = value
                    if callsign == self._qrz_lookup_callsign:
                        self._qrz_lookup_pending = False
                        self._qrz_profile = profile
                        self._qrz_own_profile = own_profile
                        self.qrz_button.setVisible(profile is not None)
                        self.qrz_button.setEnabled(profile is not None)
                elif kind == "qrz_not_found":
                    callsign = str(value)
                    if callsign == self._qrz_lookup_callsign:
                        self._qrz_lookup_pending = False
                        self._qrz_profile = None
                        self._qrz_own_profile = None
                        self.qrz_button.setVisible(False)
                elif kind == "qrz_error":
                    callsign, _message = value
                    if callsign == self._qrz_lookup_callsign:
                        self._qrz_lookup_pending = False
                        self._qrz_profile = None
                        self._qrz_own_profile = None
                        self.qrz_button.setVisible(False)
                elif kind == "qrz_log_ok":
                    source_id, callsign, qso_at, logid = value
                    self._qrz_log_pending = False
                    self.receive_service.history.record_qrz_log(source_id, callsign, qso_at, logid)
                    self.statusBar().showMessage(f"QRZ: {callsign} gespeichert · LOGID {logid}")
                    QMessageBox.information(self, "QRZ.com Logbook", f"QSO mit {callsign} wurde gespeichert.\nQRZ LOGID {logid}")
                    if hasattr(self, "history_widget"):
                        self.history_widget.refresh()
                elif kind == "qrz_log_error":
                    self._qrz_log_pending = False
                    QMessageBox.warning(self, "QRZ.com Logbook", str(value))
                    self.statusBar().showMessage(f"QRZ-Logging fehlgeschlagen: {value}")
                    if hasattr(self, "history_widget"):
                        self.history_widget.refresh()
                elif kind == "benchmark_connection_lost":
                    if self.audio_benchmark_service.connection_lost():
                        attempts = self.audio_benchmark_service.state.reconnect_attempts
                        self.statusBar().showMessage(f"Benchmark: BrandMeister getrennt, Wiederverbindung {attempts} von 5 …")
                        QTimer.singleShot(5000, self._benchmark_reconnect)
                    else:
                        self.statusBar().showMessage("Benchmark nach fünf erfolglosen Wiederverbindungen abgebrochen.")
                elif kind == "tx_beep_done":
                    QTimer.singleShot(120, self._begin_tx)
                elif kind == "tx_beep_error":
                    self.statusBar().showMessage(f"TX-Startton nicht verfügbar: {value}")
                    QTimer.singleShot(0, self._begin_tx)
                elif kind == "tx_wire_complete":
                    # Der Terminator ist tatsächlich auf dem Netz. Erst jetzt
                    # quittieren wir das Ende der Aussendung akustisch. Der
                    # Parrot-Empfang und der normale RX-Neustart laufen danach
                    # noch im Worker weiter.
                    self.tx_status.setText("Warte auf Antwort")
                    self.statusBar().showMessage("Sendung beendet; warte auf Antwort")
                    self._play_tx_stop_beeps("Sendung beendet")
                elif kind == "tx_result":
                    self._finish_tx("Sendung beendet; Empfang wieder aktiv.")
                elif kind == "tx_error":
                    self._finish_tx(f"Sendefehler: {value}")
                    QMessageBox.critical(self, "CarenDMR", f"Senden fehlgeschlagen:\n\n{value}")
                elif kind == "tx_stop_beeps_done":
                    # Nur akustische Quittung des echten TX-Endes. Der gesamte
                    # Parrot-/RX-Vorgang wird ausschließlich durch tx_result beendet.
                    pass
                elif kind == "tx_stop_beeps_error":
                    _message, error = value
                    self.statusBar().showMessage(f"TX-Endton nicht verfügbar: {error}")
        except queue.Empty:
            pass

    def _apply_state(self, state: ApplicationState) -> None:
        # Den Bedienzustand leitet der OperatingController aus demselben
        # StateStore ab; hier wird nur noch angezeigt.
        self.server_label.setText("Message Server: verbunden" if state.brandmeister_connected else "Message Server: nicht verbunden")
        self.audio_status_label.setText("Audio aktiv" if state.audio_active else "Audio nicht aktiv")
        stats = state.statistics
        self.statistics_label.setText(
            f"{stats.datagrams} Datagramme, {stats.voice_bursts} Sprachbursts, "
            f"{stats.decoded_codewords} Codewörter, {stats.decode_errors} Decodierfehler"
        )
        if state.message:
            self.last_event_label.setText(state.message)
        # Im getrennten Initialzustand enthält ApplicationState weiterhin den
        # historischen Default TG 91. Dieser darf die bereits geladenen lokalen
        # Betriebspräferenzen nicht überschreiben. Erst ein realer Verbindungs-
        # beziehungsweise Empfangszustand ist für die Anzeige maßgeblich.
        if state.talkgroup and (
            state.brandmeister_connected
            or state.connection in {
                ConnectionState.CONNECTING,
                ConnectionState.CONNECTED,
                ConnectionState.RECEIVING,
            }
        ):
            self.current_tg_label.setText(str(state.talkgroup))
            self._update_known_talkgroup_name(str(state.talkgroup))
        if state.brandmeister_connected and state.receive_active and not self._tx_active:
            self.tx_status.setText("RX")
            self.statusBar().showMessage("Empfang aktiv")
        call = state.current_call
        if call is None:
            self._request_qrz_lookup(None)
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
            callsign = contact.callsign if contact else ""
            self._request_qrz_lookup(callsign)
            self.callsign_label.setText(callsign or "Nicht gefunden")
            self.name_label.setText(contact.display_name if contact and contact.display_name else "Nicht angegeben")
            self.dmr_id_label.setText(str(call.source_id))
            location = ", ".join(part for part in (contact.city, contact.state) if contact and part) if contact else ""
            self.location_label.setText(location or "Nicht angegeben")
            self.country_label.setText(contact.country if contact and contact.country else "Nicht angegeben")
            self.target_label.setText(f"Talkgroup {call.talkgroup}, Timeslot {call.timeslot}")
            self.duration_label.setText(f"{call.elapsed_seconds:.0f} Sekunden")
            self._update_current_qso_status(call)
        self._set_controls_for_state(self.radio_state.state)
        current_radio_state = self.radio_state.state
        previous_radio_state = self._last_focus_radio_state
        self._last_focus_radio_state = current_radio_state

        if (
            current_radio_state is RadioState.CONNECTED
            and previous_radio_state not in {RadioState.CONNECTED, RadioState.TRANSMITTING}
        ):
            # Genau eine kontrollierte Ereigniskette: zuerst Fokus auf PTT,
            # danach einmal "Verbunden". Keine Zwischenansage und keine
            # Wiederholung des kompletten Betriebskontexts.
            QTimer.singleShot(0, self._focus_ptt_after_connect)
            if self._connected_announcement_pending:
                self._connected_announcement_pending = False
                QTimer.singleShot(450, lambda: self._announce_radio_state(RadioState.CONNECTED))
        elif current_radio_state not in {
            RadioState.CONNECTING,
            RadioState.DISCONNECTING,
            RadioState.TRANSMITTING,
        }:
            # CONNECTED direkt nach TX wird nicht eigens gesprochen. Der
            # PTT-Button bleibt fokussiert und liefert bereits den Zustand.
            if not (
                current_radio_state is RadioState.CONNECTED
                and previous_radio_state is RadioState.TRANSMITTING
            ):
                self._announce_radio_state(current_radio_state)


    def closeEvent(self, event: QCloseEvent) -> None:
        self._save_window_geometry()
        self._tx_pending = False
        self._tx_elapsed_timer.stop()
        if hasattr(self, "_channel_control_server"):
            self._channel_control_server.close()
        # Beendet eine laufende Sendung und den Empfang.
        self.controller.disconnect(wait_timeout=3.0)
        self.audio_benchmark_service.close()
        event.accept()


def run_gui(project_root: Path) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    apply_theme(app)
    window = MainWindow(project_root)
    window.show()
    QTimer.singleShot(150, window._focus_talkgroup)
    window._startup_announcement_timer.start(1100)
    return int(app.exec())
