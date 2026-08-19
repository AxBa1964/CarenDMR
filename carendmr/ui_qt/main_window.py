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
from datetime import datetime
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

from carendmr.application import (
    AudioSendService, ConnectionManager, EncoderService, EventService, LocalAudioLabService, QsoRecordingService,
    FavoriteService, ParrotTestService, RadioState, RadioStateMachine, ReceiveService, TalkgroupSearchService, TalkgroupCatalogService,
)
from carendmr.application.operating_preferences import OperatingPreferences, OperatingPreferencesStore
from carendmr.domain import ApplicationState, ConnectionState, DmrChannel
from carendmr.version import __version__
from carendmr.diagnostics.tx_rx_timing import initialize as initialize_tx_rx_timing, mark as timing_mark
from carendmr.ui_qt.theme import METRICS
from carendmr.accessibility.hotkeys import DEFAULT_HOTKEYS, HotkeyManager
from carendmr.ui_qt.settings_dialog import SettingsDialog
from carendmr.ui_qt.history_widget import QsoHistoryWidget
from carendmr.ui_qt.theme import apply_theme
from carendmr.ui_qt.accessibility_manager import AccessibilityManager
from carendmr.ui_qt.audio_cue import AudioCuePlayer
from carendmr.ui_qt.operating_indicators import LevelMeter, StatusIndicator
from carendmr.ui_qt.talkgroup_search_widget import TalkgroupSearchWidget
from carendmr.ui_qt.favorites_widget import FavoritesWidget
from carendmr.ui_qt.audio_tool_windows import AudioBenchmarkWindow, AudioCoachWindow, AudioLabWindow
from carendmr.benchmark import AudioBenchmarkService
from carendmr.audio import AudioDirection, TxAudioTunerSettings, TUNER_PRESETS
from carendmr.ipc.channel_control import CarenDMRChannelServer
from carendmr.qrz import QrzLookupService, QrzNotFound, QrzServiceError
from carendmr.ui_qt.qrz_window import QrzStationWindow
from carendmr.ui_qt.window_geometry import WindowGeometryManager
from carendmr.tg_monitor.instance_control import is_tg_monitor_running, send_tg_monitor_command


class MainWindow(QMainWindow):
    def __init__(self, project_root: Path) -> None:
        super().__init__()
        self.project_root = Path(project_root)
        timing_log = initialize_tx_rx_timing(self.project_root)
        timing_mark("PROGRAMMSTART_QT", f"Version {__version__}; Log={timing_log}")
        self.setWindowTitle(f"CarenDMR {__version__} – Funkgerät auf dem Desktop")
        self.resize(980, 720)

        self.events = EventService()
        self.preferences_store = OperatingPreferencesStore(self.project_root / "config" / "operating.local.json")
        self.preferences = self.preferences_store.load()
        self._selected_timeslot = self.preferences.timeslot
        self._selected_call_type = self.preferences.call_type
        self.receive_service = ReceiveService(self.project_root, events=self.events)
        self.encoder_service = EncoderService(self.project_root)
        self.audio_send_service = AudioSendService(
            self.project_root,
            mute_receive=self.receive_service.mute_audio_output,
            unmute_receive=self.receive_service.unmute_audio_output,
        )
        self.receive_service.set_output_factory(self.audio_send_service.create_pcm_output)
        self.local_audio_lab_service = LocalAudioLabService(
            self.project_root, self.audio_send_service, self.encoder_service
        )
        self.qso_recording_service = QsoRecordingService(self.project_root)
        self.audio_send_service.set_tx_pcm_observer(self.qso_recording_service.add_tx)
        # Gespeicherte Audioeinstellungen müssen nicht nur im UI stehen, sondern
        # beim Start auch tatsächlich im RX-Dienst gelten.
        self.receive_service.set_output_volume_percent(self.audio_send_service.output_volume_percent)
        self.receive_service.set_user_muted(self.audio_send_service.user_muted)
        # 0.2.1.45 Diagnose: RX-AGC startet bewusst AUS, um den beobachteten
        # leisen/hochregelnden Gesprächsanfang eindeutig gegenprüfen zu können.
        # Der Benutzer kann AGC während der Sitzung weiterhin manuell einschalten.
        self.audio_send_service.set_agc_enabled(False)
        self.receive_service.set_agc_enabled(False)
        timing_mark("RX_AGC_DIAGNOSE", "Beim Programmstart ausgeschaltet")
        self.receive_service.set_audio_debug_enabled(self.audio_send_service.audio_debug_wav_enabled)
        self.receive_service.set_audio_debug_dir_provider(lambda: self.audio_send_service.audio_test_session_dir)
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
        self.qrz_service = QrzLookupService(self.project_root / "config" / "qrz.local.json")
        self._recent_station_signature: tuple[int, ...] = ()
        self.hotkey_manager = HotkeyManager(self.project_root / "config" / "hotkeys.local.json")
        self.favorite_service = FavoriteService(self.project_root / "config" / "favorites.local.json")
        self.talkgroup_search_service = TalkgroupSearchService(self.project_root / "config" / "talkgroups.json")
        self.talkgroup_catalog_service = TalkgroupCatalogService(self.project_root / "config" / "talkgroups.json")
        self.talkgroup_search_service.set_favorites(self.favorite_service.favorites)
        self.audio_benchmark_service = AudioBenchmarkService(
            self.project_root, contact_lookup=self.receive_service.contacts.lookup,
        )
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

    def _history_worked_changed(self, source_id: int, worked: bool) -> None:
        """Synchronisiert eine Historienänderung sofort mit der Betriebsseite."""
        state = self.receive_service.state_store.get()
        self._refresh_recent_stations(force=True)
        call = state.current_call
        if call is not None and call.source_id == source_id:
            self._update_current_qso_status(call)

    @staticmethod
    def _format_qso_time(value: str) -> str:
        if not value:
            return ""
        try:
            return datetime.fromisoformat(value).astimezone().strftime("%d.%m.%Y %H:%M")
        except (TypeError, ValueError):
            return value

    def _update_current_qso_status(self, call) -> None:
        if call is None:
            self._update_current_qso_status(None)
            self.qso_mark_button.setText("Als QSO markieren")
            self.qso_mark_button.setEnabled(False)
            return
        worked_at = self.receive_service.history.last_worked_at(call.source_id)
        if worked_at:
            self.qso_status_label.setText(f"QSO: {self._format_qso_time(worked_at)}")
            self.qso_mark_button.setText("Weiteres QSO markieren")
        else:
            self.qso_status_label.setText("QSO: noch keines")
            self.qso_mark_button.setText("Als QSO markieren")
        self.qso_mark_button.setEnabled(True)

    def _mark_current_station_worked(self) -> None:
        call = self.receive_service.state_store.get().current_call
        if call is None:
            self.statusBar().showMessage("Keine aktuelle Station zum Markieren.")
            return
        contact = call.contact
        worked_at = self.receive_service.history.mark_worked(
            call.source_id,
            callsign=contact.callsign if contact else "",
            name=contact.display_name if contact else "",
            city=contact.city if contact else "",
            state=contact.state if contact else "",
            country=contact.country if contact else "",
            talkgroup=call.talkgroup,
            timeslot=call.timeslot,
        )
        self._update_current_qso_status(call)
        self._refresh_recent_stations(force=True)
        if hasattr(self, "history_widget"):
            self.history_widget.refresh()
        self.statusBar().showMessage(
            f"{contact.callsign if contact and contact.callsign else call.source_id}: "
            f"QSO {self._format_qso_time(worked_at)} gespeichert."
        )


    def _tab_changed(self, index: int) -> None:
        if index == 0:
            QTimer.singleShot(0, self.announce_operation_context)
        elif hasattr(self, "history_widget") and self.tabs.widget(index) is self.history_widget:
            self.history_widget.refresh()
            QTimer.singleShot(0, self.history_widget.announce_context)

    def _build_menu(self) -> None:
        """Ergänzt nur den Zugang zum separaten Einstellungsfenster."""
        program_menu = self.menuBar().addMenu("Programm")
        settings_action = QAction("Einstellungen …", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self._open_settings)
        program_menu.addAction(settings_action)
        program_menu.addSeparator()
        benchmark_action = QAction("Audio-Benchmark …", self)
        benchmark_action.triggered.connect(self._open_audio_benchmark)
        program_menu.addAction(benchmark_action)
        coach_action = QAction("Audio Coach …", self)
        coach_action.triggered.connect(self._open_audio_coach)
        program_menu.addAction(coach_action)
        lab_action = QAction("Live-Audiolabor …", self)
        lab_action.triggered.connect(self._open_audio_lab)
        program_menu.addAction(lab_action)
        program_menu.addSeparator()
        tg_monitor_action = QAction("TG-Monitor starten", self)
        tg_monitor_action.triggered.connect(self._start_tg_monitor)
        program_menu.addAction(tg_monitor_action)

        self.window_menu = self.menuBar().addMenu("Fenster")
        self.window_menu.aboutToShow.connect(self._rebuild_window_menu)


    def _rebuild_window_menu(self) -> None:
        self.window_menu.clear()

        main_action = QAction("CarenDMR – Hauptfenster", self)
        main_action.triggered.connect(lambda: self._bring_window_to_front(self))
        self.window_menu.addAction(main_action)

        labels = {
            "settings": "Einstellungen",
            "audio_benchmark": "Audio-Benchmark",
            "audio_coach": "Audio Coach",
            "audio_lab": "Live-Audiolabor",
            "audio_tuner": "Audio-Tuner",
            "qrz_station": (
                self._qrz_window.windowTitle()
                if self._qrz_window is not None
                else "QRZ.com – Station"
            ),
        }
        for key, widget in self.window_geometry.visible_windows():
            label = labels.get(key, widget.windowTitle() or key)
            action = QAction(label, self)
            action.triggered.connect(
                lambda _checked=False, target=widget: self._bring_window_to_front(target)
            )
            self.window_menu.addAction(action)

        if is_tg_monitor_running():
            monitor_action = QAction("TG-Monitor", self)
            monitor_action.triggered.connect(
                lambda: send_tg_monitor_command("activate")
            )
            self.window_menu.addAction(monitor_action)

        self.window_menu.addSeparator()

        front_action = QAction("Alle Fenster nach vorne", self)
        front_action.triggered.connect(self._bring_all_windows_to_front)
        self.window_menu.addAction(front_action)

        close_action = QAction("Alle Zusatzfenster schließen", self)
        close_action.triggered.connect(self._close_all_auxiliary_windows)
        self.window_menu.addAction(close_action)

        self.window_menu.addSeparator()
        reset_action = QAction("Fensterpositionen zurücksetzen", self)
        reset_action.triggered.connect(self._reset_window_positions)
        self.window_menu.addAction(reset_action)

    def _bring_window_to_front(self, widget) -> None:
        if widget is None:
            return
        if widget.isMinimized():
            widget.showNormal()
        else:
            widget.show()
        widget.raise_()
        widget.activateWindow()

    def _bring_all_windows_to_front(self) -> None:
        self._bring_window_to_front(self)
        self.window_geometry.bring_all_to_front()
        if is_tg_monitor_running():
            send_tg_monitor_command("activate")

    def _close_all_auxiliary_windows(self) -> None:
        self.window_geometry.close_all()
        if is_tg_monitor_running():
            send_tg_monitor_command("close")
        self.statusBar().showMessage("Alle Zusatzfenster wurden geschlossen.", 5000)

    def _reset_window_positions(self) -> None:
        self._close_all_auxiliary_windows()
        self.window_geometry.reset_saved()
        path = self._window_state_path()
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass

        self.showNormal()
        self.resize(980, 720)
        app = QApplication.instance()
        screens = list(app.screens()) if app is not None else []
        if screens:
            area = screens[0].availableGeometry()
            self.move(area.center() - self.rect().center())
        self.statusBar().showMessage(
            "Fensterpositionen wurden zurückgesetzt. Zusatzfenster öffnen wieder an Standardpositionen.",
            7000,
        )


    def _start_tg_monitor(self) -> None:
        """Startet den eigenständigen TG-Monitor höchstens einmal."""
        if is_tg_monitor_running():
            self.statusBar().showMessage("Der TG-Monitor läuft bereits.", 5000)
            QMessageBox.information(self, "CarenDMR", "Der TG-Monitor läuft bereits.")
            return

        script = self.project_root / "tg_monitor.py"
        if not script.is_file():
            QMessageBox.warning(self, "CarenDMR", f"TG-Monitor wurde nicht gefunden:\n{script}")
            return

        try:
            subprocess.Popen(
                [sys.executable, str(script)],
                cwd=str(self.project_root),
            )
        except OSError as error:
            QMessageBox.critical(self, "CarenDMR", f"TG-Monitor konnte nicht gestartet werden:\n\n{error}")
            return

        self.statusBar().showMessage("TG-Monitor wurde als eigenes Programm gestartet.", 5000)

    def _open_audio_benchmark(self) -> None:
        if self._audio_benchmark_window is None:
            self._audio_benchmark_window = AudioBenchmarkWindow(
                self.audio_benchmark_service,
                current_target=lambda: (
                    self._selected_talkgroup_for_benchmark(),
                    self._selected_timeslot,
                ),
                reconnect_request=self._benchmark_reconnect,
                parent=self,
            )
            self.window_geometry.register("audio_benchmark", self._audio_benchmark_window)
        self._audio_benchmark_window.show()
        self._audio_benchmark_window.raise_()
        self._audio_benchmark_window.activateWindow()

    def _open_audio_coach(self) -> None:
        if self._audio_coach_window is None:
            self._audio_coach_window = AudioCoachWindow(
                self.audio_benchmark_service,
                start_modulation_test=self._start_audio_tuner_assistant,
                cancel_modulation_test=self._cancel_audio_tuner_assistant,
                parent=self,
            )
            self.window_geometry.register("audio_coach", self._audio_coach_window)
        self._audio_coach_window.show()
        self._audio_coach_window.raise_()
        self._audio_coach_window.activateWindow()

    def _open_audio_lab(self) -> None:
        if self._audio_lab_window is None:
            self._audio_lab_window = AudioLabWindow(
                self.local_audio_lab_service,
                parent=self,
            )
            self.window_geometry.register("audio_lab", self._audio_lab_window)
        self._audio_lab_window.show()
        self._audio_lab_window.raise_()
        self._audio_lab_window.activateWindow()

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
        self.window_geometry.register("settings", dialog)
        dialog.show()


    def _settings_applied(self) -> None:
        self.preferences = self.preferences_store.load()
        self._selected_timeslot = self.preferences.timeslot
        self._selected_call_type = self.preferences.call_type
        self._reload_hotkeys()
        self._sync_radio_controls()
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
            self._sync_audio_tuner_controls()
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
        self.statusBar().showMessage(f"TX-Pegel {value} %")

    def _operation_volume_changed(self, value: int) -> None:
        self.operation_volume_value.setText(f"{value} %")
        self.audio_send_service.set_output_volume_percent(value)
        self.receive_service.set_output_volume_percent(value)
        self._save_operation_audio()

    def _operation_muted_changed(self, checked: bool) -> None:
        self.audio_send_service.set_user_muted(checked)
        self.receive_service.set_user_muted(checked)
        self._save_operation_audio()
        message = "Empfang stumm" if checked else "Empfangston aktiv"
        self.statusBar().showMessage(message)
        self.accessibility.announce_toggle(self.operation_muted_check, "Empfang stumm", checked)

    def _operation_agc_changed(self, checked: bool) -> None:
        self.audio_send_service.set_agc_enabled(checked)
        self.receive_service.set_agc_enabled(checked)
        self._save_operation_audio()
        message = "AGC aktiv" if checked else "AGC ausgeschaltet"
        self.statusBar().showMessage(message)
        self.accessibility.announce_toggle(self.operation_agc_check, "AGC", checked)

    def _build_audio_tuner_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("DMR Audio-Tuner")
        dialog.setModal(False)
        dialog.setMinimumWidth(560)

        outer = QVBoxLayout(dialog)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        heading = QLabel("DMR AUDIO-TUNER")
        heading.setObjectName("sectionTitle")
        outer.addWidget(heading)

        intro = QLabel("Klangprofil für den nächsten TX")
        intro.setObjectName("secondaryText")
        outer.addWidget(intro)

        card = QFrame(dialog)
        card.setObjectName("card")
        layout = QGridLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(9)
        layout.setColumnStretch(1, 1)

        self.audio_tuner_profile = QComboBox(card)
        self.audio_tuner_profile.addItems(["Neutral", "Klar", "DX", "Warm", "Eigene"])
        self.audio_tuner_profile.setAccessibleName("Audio-Profil")
        profile_caption = QLabel("Profil")
        profile_caption.setObjectName("fieldCaption")
        layout.addWidget(profile_caption, 0, 0)
        layout.addWidget(self.audio_tuner_profile, 0, 1)
        self.audio_tuner_reset_button = QPushButton("Zurücksetzen", card)
        layout.addWidget(self.audio_tuner_reset_button, 0, 2)

        self.audio_tuner_sliders = {}
        tuner_specs = (
            ("low_db", "Tiefen", -12, 12, " dB"),
            ("mids_db", "Sprachmitten", -12, 12, " dB"),
            ("presence_db", "Präsenz", -12, 12, " dB"),
            ("high_db", "Höhen", -12, 12, " dB"),
            ("dynamics_percent", "Dynamik", 0, 100, " %"),
            ("limiter_percent", "Limiter", 0, 100, " %"),
            ("ptt_lead", "PTT-Vorlauf", 0, 50, " s"),
        )
        for row, (key, label, minimum, maximum, suffix) in enumerate(tuner_specs, start=1):
            caption = QLabel(label)
            caption.setObjectName("fieldCaption")
            slider = QSlider(Qt.Orientation.Horizontal, card)
            slider.setRange(minimum, maximum)
            slider.setAccessibleName(label)
            value_label = QLabel("0" + suffix, card)
            value_label.setObjectName("tunerValue")
            value_label.setMinimumWidth(72)
            value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            layout.addWidget(caption, row, 0)
            layout.addWidget(slider, row, 1)
            layout.addWidget(value_label, row, 2)
            self.audio_tuner_sliders[key] = (slider, value_label, suffix)

        outer.addWidget(card)
        hint = QLabel("Änderungen werden gespeichert und wirken ab dem nächsten Senden.")
        hint.setObjectName("secondaryText")
        hint.setWordWrap(True)
        outer.addWidget(hint)

        dialog.setLayout(outer)
        dialog.adjustSize()
        dialog.setFixedHeight(dialog.sizeHint().height())
        self._audio_tuner_dialog = dialog
        self.window_geometry.register("audio_tuner", dialog)

    def _show_audio_tuner_dialog(self) -> None:
        if self._audio_tuner_dialog is None:
            return
        self._sync_audio_tuner_controls()
        self._audio_tuner_dialog.show()
        self._audio_tuner_dialog.raise_()
        self._audio_tuner_dialog.activateWindow()

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

    def _sync_audio_tuner_controls(self) -> None:
        if not hasattr(self, "audio_tuner_profile"):
            return
        settings = self.audio_send_service.tx_audio_tuner_settings
        widgets = [self.audio_tuner_profile] + [item[0] for item in self.audio_tuner_sliders.values()]
        for widget in widgets:
            widget.blockSignals(True)
        try:
            index = self.audio_tuner_profile.findText(settings.profile)
            self.audio_tuner_profile.setCurrentIndex(index if index >= 0 else self.audio_tuner_profile.findText("Eigene"))
            values = {
                "low_db": round(settings.low_db), "mids_db": round(settings.mids_db),
                "presence_db": round(settings.presence_db), "high_db": round(settings.high_db),
                "dynamics_percent": settings.dynamics_percent, "limiter_percent": settings.limiter_percent,
                "ptt_lead": round(self.preferences.screenreader_ptt_lead_in_seconds * 10),
            }
            for key, value in values.items():
                slider, label, suffix = self.audio_tuner_sliders[key]
                slider.setValue(int(value))
                shown = f"{value / 10:.1f}" if key == "ptt_lead" else f"{int(value):+d}" if key.endswith("_db") else str(int(value))
                label.setText(shown + suffix)
        finally:
            for widget in widgets:
                widget.blockSignals(False)

    def _audio_tuner_profile_changed(self, name: str) -> None:
        if name in TUNER_PRESETS:
            self._apply_audio_tuner_preset(name)

    def _apply_audio_tuner_preset(self, name: str) -> None:
        settings = self.audio_send_service.set_tx_audio_tuner_preset(name)
        self.audio_send_service.save_settings()
        self._sync_audio_tuner_controls()
        self.statusBar().showMessage(f"Audio-Profil {settings.profile} aktiv – wirkt ab dem nächsten TX.", 4000)

    def _audio_tuner_slider_changed(self, changed_key: str) -> None:
        for key, (slider, label, suffix) in self.audio_tuner_sliders.items():
            value = slider.value()
            shown = f"{value / 10:.1f}" if key == "ptt_lead" else f"{value:+d}" if key.endswith("_db") else str(value)
            label.setText(shown + suffix)
        if changed_key == "ptt_lead":
            lead = self.audio_tuner_sliders["ptt_lead"][0].value() / 10.0
            self.preferences = OperatingPreferences(
                self.preferences.talkgroup, self.preferences.timeslot, self.preferences.call_type,
                self.preferences.speech_enabled, lead
            )
            self.preferences_store.save(self.preferences)
        else:
            values = {key: item[0].value() for key, item in self.audio_tuner_sliders.items()}
            settings = TxAudioTunerSettings(
                profile="Eigene", low_db=values["low_db"], mids_db=values["mids_db"],
                presence_db=values["presence_db"], high_db=values["high_db"],
                dynamics_percent=values["dynamics_percent"], limiter_percent=values["limiter_percent"],
            )
            self.audio_send_service.set_tx_audio_tuner_settings(settings)
            self.audio_send_service.save_settings()
            if self.audio_tuner_profile.currentText() != "Eigene":
                self.audio_tuner_profile.blockSignals(True)
                self.audio_tuner_profile.setCurrentText("Eigene")
                self.audio_tuner_profile.blockSignals(False)
        self.statusBar().showMessage("Eigene Audio-Einstellung gespeichert – wirkt ab dem nächsten TX.", 3000)

    def _prepare_audio_tuner_parrot(self) -> None:
        if self._tx_active or self._tx_pending:
            self.statusBar().showMessage("Parrot kann während TX nicht vorbereitet werden.")
            return
        channel = DmrChannel(target=9990, timeslot=2, call_type="private", name="Parrot")
        self._set_current_dmr_channel(channel)
        self.tabs.setCurrentIndex(0)
        self.connect_button.setFocus()
        self.statusBar().showMessage("Parrot vorbereitet. Verbinden, TX drücken und Referenztext sprechen.")

    def _start_audio_tuner_assistant(self) -> None:
        try:
            self.audio_send_service.arm_audio_test(pre_roll_seconds=0.0)
        except Exception as exc:
            QMessageBox.warning(self, "Audio-Assistent", str(exc))
            return
        self._prepare_audio_tuner_parrot()
        self.statusBar().showMessage("Audio Coach bereit. Parrot verbinden und genau eine Sendung durchführen.")

    def _cancel_audio_tuner_assistant(self) -> None:
        """Beendet einen geführten Audiotest und räumt jeden Zwischenzustand auf."""
        self.audio_send_service.cancel_audio_test()
        if self._tx_pending:
            self._cancel_pending_tx()
        if self._tx_active:
            self._stop_tx()
        self.statusBar().showMessage("Modulationstest abgebrochen; Empfang wird wiederhergestellt.")

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

    def _refresh_segment_style(self, button: QPushButton, selected: bool) -> None:
        """Visualisiert eine Auswahl, ohne dem Widget eine Checkbox-Rolle zu geben."""
        button.setProperty("selected", selected)
        button.style().unpolish(button)
        button.style().polish(button)

    def _sync_radio_controls(self) -> None:
        """Synchronisiert Auswahloptik, Fokuspfad und kurze Screenreader-Namen."""
        controls = (
            (self.ts1_radio, self._selected_timeslot == 1, "Timeslot 1"),
            (self.ts2_radio, self._selected_timeslot == 2, "Timeslot 2"),
            (self.group_radio, self._selected_call_type == "group", "Gruppenruf"),
            (self.private_radio, self._selected_call_type == "private", "Privatruf"),
        )
        for button, selected, label in controls:
            self._refresh_segment_style(button, selected)
            button.setProperty("radioFlag", True)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.setAccessibleName("")
            button.setAccessibleDescription("")
        if hasattr(self, "current_channel_meta_label"):
            call_text = "Gruppe" if self._selected_call_type == "group" else "Privat"
            self.current_channel_meta_label.setText(
                f"TS{self._selected_timeslot} · {call_text}"
            )
        if hasattr(self, "operation_gain_slider") and hasattr(self, "connect_button"):
            self._restore_tab_order()

    def _select_timeslot(self, timeslot: int, *, announce: bool = False) -> None:
        if timeslot not in {1, 2} or not self.radio_state.snapshot().can_edit_parameters:
            return
        self._selected_timeslot = timeslot
        self._sync_radio_controls()
        self._persist_current_target()
        if announce:
            self.accessibility.announce_timeslot(self.connection_label, timeslot)

    def _select_call_type(self, call_type: str, *, announce: bool = False) -> None:
        if call_type not in {"group", "private"} or not self.radio_state.snapshot().can_edit_parameters:
            return
        self._selected_call_type = call_type
        self._sync_radio_controls()
        self._persist_current_target()
        if announce:
            self.accessibility.announce_call_type(self.connection_label, call_type)

    def _persist_current_target(self) -> None:
        """Speichert TG, Timeslot und Rufart ohne den Fokusablauf zu verändern."""
        try:
            self._save_preferences()
        except Exception as error:
            self.statusBar().showMessage(f"DMR-Kanal konnte nicht gespeichert werden: {error}")

    def _target(self) -> tuple[int, int, str]:
        text = self.current_tg_label.text().strip()
        if not text or not text.isdigit() or int(text) <= 0:
            raise ValueError("Bitte eine gültige Talkgroup eingeben.")
        return int(text), self._selected_timeslot, self._selected_call_type

    def _update_talkgroup_accessibility(self, value: str) -> None:
        """Hält nur den zugänglichen Feldkontext aktuell, ohne Ansage."""
        spoken = self.accessibility.formatter.digits(value)
        description = f"Aktueller Wert, Ziffern {spoken}" if spoken else "Feld ist leer"
        self.tg_edit.setAccessibleDescription(description)

    def _announce_pending_talkgroup(self) -> None:
        value = self.tg_edit.text().strip()
        if value:
            self.accessibility.announce_pending_talkgroup(self.tg_edit, value)

    def _focus_talkgroup(self) -> None:
        """Setzt nach dem Trennen den Fokus in das Feld für eine neue Talkgroup."""
        self.tg_edit.setFocus()
        self.tg_edit.selectAll()

    def _focus_ptt_after_connect(self, retries: int = 12) -> None:
        """Setzt nach erfolgreichem Verbinden den Fokus zuverlässig auf PTT.

        Die Encoder-Prüfung kann wenige Millisekunden später fertig werden.
        Solange der Button noch gesperrt ist, wird deshalb kurz erneut versucht.
        """
        if self.radio_state.state is not RadioState.CONNECTED:
            return
        if self.ptt_button.isEnabled():
            self.ptt_button.setFocus(Qt.FocusReason.ShortcutFocusReason)
            return
        if retries > 0:
            QTimer.singleShot(100, lambda: self._focus_ptt_after_connect(retries - 1))

    def _restore_saved_dmr_channel(self) -> None:
        """Stellt den zuletzt gespeicherten DMR-Kanal vollständig wieder her.

        Der gespeicherte Zustand enthält nur Ziel, Timeslot und Rufart. Der
        Anzeigename wird deshalb beim Start erneut aus dem lokalen
        Talkgroup-Verzeichnis aufgelöst. Unbekannte Ziele bleiben namenlos.
        """
        known = self._known_channel_for_target(self.preferences.talkgroup)
        channel = DmrChannel(
            target=self.preferences.talkgroup,
            timeslot=self.preferences.timeslot,
            call_type=self.preferences.call_type,
            name=known.name if known else "",
            country=known.country if known else "",
            description=known.description if known else "",
        )
        self._set_current_dmr_channel(channel, clear_input=False)

    def _known_channel_for_target(self, target: int):
        """Liefert den ersten bekannten Kanal für eine Zielnummer oder ``None``."""
        for channel in self.talkgroup_search_service.channels:
            if channel.target == target:
                return channel.normalized()
        return None

    def _set_current_dmr_channel(self, channel, *, clear_input: bool = True) -> None:
        """Aktualisiert den aktuell gewählten DMR-Kanal immer vollständig.

        Diese Methode ist die einzige Quelle für TG, Name, Timeslot und Rufart
        auf der Betriebsseite. Dadurch bleiben Suche, manuelle Eingabe und
        spätere Favoriten synchron.
        """
        normalized = channel.normalized()
        previous = self._current_dmr_channel
        if (
            previous is not None
            and self.qso_recording_service.is_active
            and (previous.target, previous.timeslot, previous.call_type)
                != (normalized.target, normalized.timeslot, normalized.call_type)
        ):
            self._stop_qso_recording("Mitschnitt wegen Zielwechsel beendet")
        self._current_dmr_channel = normalized
        self.current_tg_label.setText(str(normalized.target))
        self.current_tg_name_label.setText(normalized.name or "")
        self._selected_timeslot = normalized.timeslot
        self._selected_call_type = normalized.call_type
        self._sync_radio_controls()
        if clear_input:
            self.tg_edit.clear()
            self._update_talkgroup_accessibility("")
        if hasattr(self, "favorite_button"):
            self._update_favorite_button()

    def _update_known_talkgroup_name(self, value: str) -> None:
        """Aktualisiert den Namen zur bereits übernommenen aktuellen TG."""
        text = str(value).strip()
        channel = self._known_channel_for_target(int(text)) if text.isdigit() else None
        self.current_tg_name_label.setText(channel.name if channel else "")

    def _refresh_favorites(self) -> None:
        """Aktualisiert nur Favoriten-Metadaten der gemeinsamen Kanalliste.

        Der Audio-Benchmark ist eine langlebige Hauptfenster-Komponente. Er darf
        beim Aktualisieren der Favoriten nicht neu erzeugt werden, weil das
        Benchmark-Widget sonst am alten Service hängt, während der RX-Pfad den
        neuen Service beliefert.
        """
        self.talkgroup_search_service.set_favorites(self.favorite_service.favorites)
        if hasattr(self, "favorites_widget"):
            self.favorites_widget.refresh()
        self._update_favorite_button()
        self._refresh_favorite_hot_buttons()
        self._refresh_favorite_combo()

    def _refresh_favorite_combo(self) -> None:
        if not hasattr(self, "favorite_combo"):
            return
        combo = self.favorite_combo
        combo.blockSignals(True)
        try:
            combo.clear()
            combo.addItem("Alle Favoriten …", None)
            for favorite in self.favorite_service.favorites:
                kind = "G" if favorite.call_type == "group" else "P"
                text = f"{favorite.display_name}  ·  TG {favorite.target} / TS{favorite.timeslot} / {kind}"
                combo.addItem(text, favorite)
            combo.setCurrentIndex(0)
            combo.setEnabled(len(self.favorite_service.favorites) > 0)
        finally:
            combo.blockSignals(False)

    def _favorite_combo_selected(self, index: int) -> None:
        if index <= 0:
            return
        favorite = self.favorite_combo.itemData(index)
        self.favorite_combo.blockSignals(True)
        self.favorite_combo.setCurrentIndex(0)
        self.favorite_combo.blockSignals(False)
        if favorite is None:
            return
        self._activate_favorite(favorite, source_label="Favorit")

    def _activate_favorite(self, favorite, *, source_label: str) -> None:
        if self._tx_active or self._tx_pending or self._tx_stopping:
            self.statusBar().showMessage(f"{source_label} ist während TX nicht möglich.")
            return
        channel = favorite.to_dmr_channel()
        state = self.radio_state.state
        if state in {RadioState.CONNECTING, RadioState.DISCONNECTING}:
            self.statusBar().showMessage(
                f"{source_label} wartet, bis der aktuelle Verbindungswechsel beendet ist."
            )
            return
        if state is RadioState.CONNECTED:
            self._pending_hot_favorite = channel
            self.statusBar().showMessage(
                f"{source_label} {favorite.display_name}: trenne aktuelle Verbindung …"
            )
            self._disconnect()
            return
        self._connect_hot_favorite(channel)

    def _refresh_favorite_hot_buttons(self) -> None:
        if not hasattr(self, "favorite_hot_buttons"):
            return
        favorites = self.favorite_service.favorites[:3]
        for index, button in enumerate(self.favorite_hot_buttons):
            if index >= len(favorites):
                button.setText("–")
                button.setEnabled(False)
                button.setToolTip("Kein Favorit an dieser Position")
                continue
            favorite = favorites[index]
            kind = "G" if favorite.call_type == "group" else "P"
            name = favorite.display_name
            # Kurzer sichtbarer Name; alle technischen Werte bleiben im Tooltip/AccessibleName.
            button.setText(name)
            detail = f"TG {favorite.target} · TS{favorite.timeslot} · {kind}"
            button.setToolTip(detail)
            button.setAccessibleName(f"Schnellwahl {index + 1}: {name}, {detail}")
            button.setEnabled(True)

    def _activate_hot_favorite(self, index: int) -> None:
        favorites = self.favorite_service.favorites
        if not 0 <= index < min(3, len(favorites)):
            return
        self._activate_favorite(favorites[index], source_label="Schnellwahl")

    def _connect_hot_favorite(self, channel) -> None:
        try:
            normalized = channel.normalized()
        except (AttributeError, TypeError, ValueError):
            self._pending_hot_favorite = None
            return
        self._set_current_dmr_channel(normalized)
        try:
            self._save_preferences()
        except Exception as error:
            self._pending_hot_favorite = None
            QMessageBox.warning(self, "CarenDMR", str(error))
            return
        self._pending_hot_favorite = None
        self.tabs.setCurrentIndex(0)
        self.statusBar().showMessage(
            f"Schnellwahl {normalized.name or normalized.target}: verbinde TG {normalized.target}, "
            f"TS{normalized.timeslot}, {'Gruppe' if normalized.is_group_call else 'Privat'} …"
        )
        self._connect()

    def _handle_external_channel_request(self, channel: DmrChannel) -> tuple[bool, str]:
        """Übernimmt einen Kanal aus dem eigenständigen TG-Monitor."""
        try:
            normalized = channel.normalized()
        except (AttributeError, TypeError, ValueError) as error:
            return False, f"Ungültiger DMR-Kanal: {error}"

        if self._tx_active or self._tx_pending or self._tx_stopping:
            return False, "CarenDMR sendet gerade. Kanalwechsel wurde nicht ausgeführt."

        state = self.radio_state.state
        if state in {RadioState.CONNECTING, RadioState.DISCONNECTING}:
            return False, "CarenDMR wechselt gerade die Verbindung. Bitte gleich erneut versuchen."

        if state is RadioState.CONNECTED:
            self._pending_external_channel = normalized
            self.statusBar().showMessage(f"TG-Monitor: trenne für TG {normalized.target} …")
            self._disconnect()
            return True, f"TG {normalized.target} wird in CarenDMR übernommen."

        if state in {RadioState.DISCONNECTED, RadioState.ERROR}:
            QTimer.singleShot(0, lambda selected=normalized: self._connect_external_channel(selected))
            return True, f"TG {normalized.target} wird in CarenDMR übernommen."

        return False, "CarenDMR ist momentan nicht bereit für einen Kanalwechsel."

    def _connect_external_channel(self, channel: DmrChannel) -> None:
        try:
            normalized = channel.normalized()
        except (AttributeError, TypeError, ValueError):
            self._pending_external_channel = None
            return

        if self._tx_active or self._tx_pending or self._tx_stopping:
            self._pending_external_channel = None
            self.statusBar().showMessage("TG-Monitor-Kanalwechsel wegen TX verworfen.")
            return
        if self.radio_state.state not in {RadioState.DISCONNECTED, RadioState.ERROR}:
            return

        self._set_current_dmr_channel(normalized)
        try:
            self._save_preferences()
        except Exception as error:
            self._pending_external_channel = None
            QMessageBox.warning(self, "CarenDMR", str(error))
            return

        self._pending_external_channel = None
        self.tabs.setCurrentIndex(0)
        self.statusBar().showMessage(
            f"TG-Monitor: verbinde TG {normalized.target}, TS{normalized.timeslot}, "
            f"{'Gruppe' if normalized.is_group_call else 'Privat'} …"
        )
        self._connect()

    def _update_favorite_button(self) -> None:
        if not hasattr(self, "favorite_button") or self._current_dmr_channel is None:
            return
        channel = self._current_dmr_channel
        favorite = self.favorite_service.find(channel.target, channel.timeslot, channel.call_type)
        self.favorite_button.setText("★" if favorite else "☆")
        action = "bearbeiten" if favorite else "speichern"
        self.favorite_button.setAccessibleName(f"Aktuellen DMR-Kanal als Favorit {action}")

    def _edit_current_favorite(self) -> None:
        channel = self._current_dmr_channel
        if channel is None:
            return
        if self.favorites_widget.add_channel(channel):
            self._refresh_favorites()
            self.statusBar().showMessage("Favorit gespeichert.")

    def _apply_favorite_channel(self, channel) -> None:
        self._apply_selected_channel(channel)
        self.tabs.setCurrentIndex(0)
        self.connect_button.setFocus()

    def _apply_selected_channel(self, channel) -> None:
        """Übernimmt einen Treffer vollständig als DMR-Kanal, ohne zu verbinden."""
        try:
            normalized = channel.normalized()
        except (AttributeError, TypeError, ValueError):
            return
        if not self.radio_state.snapshot().can_edit_parameters:
            return
        self._set_current_dmr_channel(normalized)
        try:
            self._save_preferences()
        except Exception as error:
            QMessageBox.warning(self, "CarenDMR", str(error))
            return
        self.connect_button.setFocus()
        target_kind = "Talkgroup" if normalized.is_group_call else "DMR-ID"
        channel_name = f" {normalized.name}" if normalized.name else ""
        self.statusBar().showMessage(
            f"{target_kind}{channel_name} {normalized.target}, TS{normalized.timeslot}, "
            f"{'Gruppe' if normalized.is_group_call else 'Privat'} übernommen."
        )

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
        target = int(text)
        known = self._known_channel_for_target(target)
        if known is None:
            known = DmrChannel(target, self._selected_timeslot, self._selected_call_type)
        else:
            # Manuelle Nummerneingabe ändert TS und Rufart nicht heimlich.
            known = DmrChannel(
                known.target,
                self._selected_timeslot,
                self._selected_call_type,
                known.name,
                known.country,
                known.description,
            )
        self._set_current_dmr_channel(known)
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
        self.preferences_store.save(OperatingPreferences(tg, ts, call_type, False, self.preferences.screenreader_ptt_lead_in_seconds))
        self.preferences = self.preferences_store.load()
        self._selected_timeslot = self.preferences.timeslot
        self._selected_call_type = self.preferences.call_type

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
        self.ptt_button.setText("TX")
        if state is RadioState.TRANSMITTING and self._tx_active:
            ptt_state = "tx"
        elif state is RadioState.CONNECTED:
            ptt_state = "ready"
        else:
            ptt_state = "idle"
        self.ptt_button.setProperty("visualState", ptt_state)
        self.ptt_button.style().unpolish(self.ptt_button)
        self.ptt_button.style().polish(self.ptt_button)

        if state in {RadioState.CONNECTED, RadioState.TRANSMITTING}:
            connect_text = "Trennen"
        elif state is RadioState.CONNECTING:
            connect_text = "Verbindung wird hergestellt"
        elif state is RadioState.DISCONNECTING:
            connect_text = "Verbindung wird getrennt"
        else:
            connect_text = "Verbinden"
        self.connect_button.setText(connect_text)
        self.connect_button.setAccessibleName(connect_text)
        self.connect_button.setAccessibleDescription("")

        # Der fokussierte Verbindungsbutton bleibt während Aufbau/Trennung
        # fokussierbar. Ein Deaktivieren würde Qt den Fokus kurz auf Mic-Gain
        # verschieben lassen. _toggle_connection() ignoriert Übergangszustände.
        self.connect_button.setEnabled(state is not RadioState.TRANSMITTING)
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
        if state is RadioState.ERROR:
            badge_state = "error"
        self.connection_indicator.set_state(badge_state)
        self.connect_button.style().unpolish(self.connect_button)
        self.connect_button.style().polish(self.connect_button)
        if state not in {RadioState.CONNECTED, RadioState.TRANSMITTING}:
            self.rx_level_meter.reset()
        if state is not RadioState.TRANSMITTING:
            self.mic_level_meter.reset()

    def _toggle_qso_recording(self) -> None:
        if self.qso_recording_service.is_active:
            self._stop_qso_recording("Mitschnitt beendet")
            return
        path = self.qso_recording_service.start()
        self.record_button.setText("Mitschnitt beenden")
        self.record_button.setAccessibleName("QSO-Mitschnitt beenden")
        self.statusBar().showMessage(f"Mitschnitt läuft: {path.name}")

    def _stop_qso_recording(self, reason: str) -> None:
        if not self.qso_recording_service.is_active:
            return
        path = self.qso_recording_service.stop()
        self.record_button.setText("Mitschnitt starten")
        self.record_button.setAccessibleName("QSO-Mitschnitt starten")
        if path is not None:
            self.statusBar().showMessage(f"{reason}: {path.name}")
        else:
            self.statusBar().showMessage(f"{reason}: keine Audiodaten aufgezeichnet")

    def _toggle_connection(self) -> None:
        state = self.radio_state.state
        if state in {RadioState.CONNECTED, RadioState.TRANSMITTING}:
            self._disconnect()
        elif state in {RadioState.DISCONNECTED, RadioState.ERROR}:
            self._announce_pending_talkgroup()
            if self._apply_pending_talkgroup():
                self._connect()

    def _connect(self) -> None:
        try:
            tg, ts, call_type = self._target()
            self._save_preferences()
        except Exception as error:
            QMessageBox.warning(self, "CarenDMR", str(error))
            return
        self._startup_announcement_timer.stop()
        self._connected_announcement_pending = True
        self.radio_state.synchronize(RadioState.CONNECTING)
        self.connection_indicator.set_state("busy")
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
        self._stop_qso_recording("Mitschnitt wegen Trennen beendet")
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
        if self._tx_stopping:
            return
        if self._tx_pending:
            self._cancel_pending_tx()
        elif self._tx_active:
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

        # Bei aktivem Screenreader bekommt dessen kurze RX-Ansage Zeit, bevor
        # das Mikrofon geöffnet wird. Qt liefert keinen verlässlichen Callback
        # für das Ende einer Narrator-/VoiceOver-Ansage; ein kurzer Vorlauf ist
        # deshalb die robuste, plattformneutrale Lösung.
        self._tx_pending = True
        self.ptt_button.setText("TX")
        self.ptt_button.setProperty("visualState", "pending")
        self.ptt_button.style().unpolish(self.ptt_button)
        self.ptt_button.style().polish(self.ptt_button)
        self.tx_status.setText("TX wird vorbereitet")
        self.statusBar().showMessage("TX wird vorbereitet")
        # Die konfigurierte Vorlaufzeit ist zugleich der explizite Accessibility-Testmodus.
        # Die automatische Qt-Erkennung ist unter Windows/Narrator nicht zuverlässig genug.
        delay_ms = int(round(self.preferences.screenreader_ptt_lead_in_seconds * 1000))
        QTimer.singleShot(delay_ms, self._play_tx_ready_beep if delay_ms > 0 else self._begin_tx)

    def _play_tx_ready_beep(self) -> None:
        """Spielt den lokalen Start-Beep; TX beginnt erst nach dessen Ende."""
        if not self._tx_pending or self.radio_state.state is not RadioState.CONNECTED:
            return

        def worker() -> None:
            try:
                self.audio_cues.play_tx_start()
                self._updates.put(("tx_beep_done", None))
            except Exception as error:
                self._updates.put(("tx_beep_error", error))

        Thread(target=worker, name="CarenDMR-TX-Start-Cue", daemon=True).start()

    def _play_tx_stop_beeps(self, message: str) -> None:
        """Spielt nach geschlossenem TX zwei lokale Quittungstöne."""
        def worker() -> None:
            try:
                self.audio_cues.play_tx_stop()
                self._updates.put(("tx_stop_beeps_done", message))
            except Exception as error:
                self._updates.put(("tx_stop_beeps_error", (message, error)))

        Thread(target=worker, name="CarenDMR-TX-Stop-Cue", daemon=True).start()

    def _begin_tx(self) -> None:
        if not self._tx_pending or self.radio_state.state is not RadioState.CONNECTED:
            return
        self._tx_pending = False
        self._tx_stop_event = Event()
        self._tx_active = True
        self._tx_stopping = False
        self._tx_elapsed_seconds = 0
        self._tx_warning_played = False
        self._tx_elapsed_timer.start()
        self.ptt_button.setText("TX")
        self.ptt_button.setProperty("visualState", "tx")
        self.ptt_button.style().unpolish(self.ptt_button)
        self.ptt_button.style().polish(self.ptt_button)
        self.radio_state.synchronize(RadioState.TRANSMITTING)
        self.tx_status.setText("TX")
        self.statusBar().showMessage("TX")
        self._set_controls_for_state(self.radio_state.state)
        stop_event = self._tx_stop_event

        def worker() -> None:
            try:
                result = self.connection_manager.run_parrot_hold_to_talk(
                    stop_event,
                    level_callback=lambda level: self._updates.put(("mic_level", level)),
                    optimize=True,
                    tx_complete_callback=lambda: self._updates.put(("tx_wire_complete", None)),
                )
                self._updates.put(("tx_result", result))
            except Exception as error:
                self._updates.put(("tx_error", error))
        Thread(target=worker, name="CarenDMR-Qt-TX", daemon=True).start()

    def _cancel_pending_tx(self) -> None:
        self._tx_pending = False
        self.ptt_button.setText("TX")
        self.ptt_button.setProperty("visualState", "ready")
        self.ptt_button.style().unpolish(self.ptt_button)
        self.ptt_button.style().polish(self.ptt_button)
        self.tx_status.setText("RX")
        self.statusBar().showMessage("RX")

    def _increment_tx_elapsed(self) -> None:
        if not self._tx_active:
            self._tx_elapsed_timer.stop()
            return
        self._tx_elapsed_seconds += 1
        limit = int(self.audio_send_service.tx_safety_limit_seconds)
        remaining = limit - self._tx_elapsed_seconds if limit > 0 else None
        if remaining is not None and 0 < remaining <= 10:
            self.ptt_button.setText(f"TX   {self._tx_elapsed_seconds} s   ·   noch {remaining} s")
            self.ptt_button.setProperty("visualState", "warning")
            self.ptt_button.style().unpolish(self.ptt_button)
            self.ptt_button.style().polish(self.ptt_button)
            if not self._tx_warning_played:
                self._tx_warning_played = True
                self.statusBar().showMessage("TX-Zeitbegrenzung: noch 10 Sekunden")
                try:
                    Thread(
                        target=self.audio_cues.play_tx_warning,
                        name="CarenDMR-TX-Warnung",
                        daemon=True,
                    ).start()
                except Exception:
                    pass
        else:
            self.ptt_button.setText(f"TX   {self._tx_elapsed_seconds} s")


    def _stop_tx(self) -> None:
        if not self._tx_active:
            return
        if self._tx_stop_event is not None:
            self._tx_stop_event.set()
        self._tx_stopping = True
        # Bediener sieht sofort, dass TX beendet wurde. Der Worker darf im
        # Hintergrund noch sauber auslaufen, aber Zähler und TX-Anzeige stoppen.
        self._tx_elapsed_timer.stop()
        self._tx_elapsed_seconds = 0
        self._tx_warning_played = False
        self.ptt_button.setEnabled(False)
        self.ptt_button.setText("TX")
        self.ptt_button.setProperty("visualState", "pending")
        self.ptt_button.style().unpolish(self.ptt_button)
        self.ptt_button.style().polish(self.ptt_button)
        self.tx_status.setText("TX wird beendet")
        self.statusBar().showMessage("Sendung wird beendet")

    def _finish_tx(self, message: str) -> None:
        self._tx_active = False
        self._tx_stopping = False
        self._tx_pending = False
        self._tx_stop_event = None
        self._tx_elapsed_timer.stop()
        self._tx_elapsed_seconds = 0
        self._tx_warning_played = False
        state = RadioState.CONNECTED if self.receive_service.is_running else RadioState.DISCONNECTED
        self.radio_state.synchronize(state)
        self.ptt_button.setText("TX")
        self.ptt_button.setProperty("visualState", "ready" if state is RadioState.CONNECTED else "idle")
        self.ptt_button.style().unpolish(self.ptt_button)
        self.ptt_button.style().polish(self.ptt_button)
        self.tx_status.setText("RX")
        self.statusBar().showMessage(message)
        self._set_controls_for_state(state)
        # Keine zusätzliche RX-Ansage; der fokussierte Button meldet nur TX.

    def _verify_encoder(self) -> None:
        def worker() -> None:
            try:
                diagnostics = self.encoder_service.verify_configured()
                self._updates.put(("encoder_ready", diagnostics))
            except Exception as error:
                self._updates.put(("encoder_error", error))
        Thread(target=worker, name="CarenDMR-Qt-Encoder", daemon=True).start()

    def _toggle_timeslot(self) -> None:
        self._select_timeslot(2 if self._selected_timeslot == 1 else 1, announce=True)

    def _toggle_call_type(self) -> None:
        self._select_call_type("private" if self._selected_call_type == "group" else "group", announce=True)

    def _selected_talkgroup_for_benchmark(self) -> int:
        return int(self.receive_service.target_talkgroup or self.preferences.talkgroup)

    def _benchmark_call_activity(self, activity) -> None:
        self.audio_send_service.observe_audio_test_call_activity(activity)
        if activity.active:
            self.audio_benchmark_service.stream_started(
                activity.source_id, activity.talkgroup, activity.timeslot, activity.stream_id,
            )
        else:
            self.audio_benchmark_service.stream_finished(
                activity.source_id, activity.talkgroup, activity.timeslot, activity.stream_id,
            )

    def _benchmark_pcm(self, source_id, talkgroup, timeslot, stream_id, samples, corrected_errors=0) -> None:
        self.audio_send_service.observe_audio_test_pcm(
            source_id, talkgroup, timeslot, stream_id, samples, corrected_errors
        )
        self.audio_benchmark_service.add_pcm(
            source_id, talkgroup, timeslot, stream_id, samples,
            corrected_errors=corrected_errors,
        )
        self.qso_recording_service.add_rx(samples)

    def _request_qrz_lookup(self, callsign: str | None) -> None:
        normalized = str(callsign or "").strip().upper()
        if not normalized:
            self._qrz_lookup_callsign = ""
            self._qrz_lookup_pending = False
            self._qrz_profile = None
            self._qrz_own_profile = None
            self.qrz_button.setVisible(False)
            return
        if normalized == self._qrz_lookup_callsign and (
            self._qrz_lookup_pending or self._qrz_profile is not None
        ):
            return

        self._qrz_lookup_callsign = normalized
        self._qrz_lookup_pending = True
        self._qrz_profile = None
        self._qrz_own_profile = None
        self.qrz_button.setVisible(False)

        if not self.qrz_service.configured:
            self._qrz_lookup_pending = False
            return

        def worker() -> None:
            try:
                profile = self.qrz_service.lookup(normalized)
                try:
                    own_profile = self.qrz_service.lookup_own_station()
                except QrzServiceError:
                    own_profile = None
                self._updates.put(("qrz_result", (normalized, profile, own_profile)))
            except QrzNotFound:
                self._updates.put(("qrz_not_found", normalized))
            except QrzServiceError as error:
                self._updates.put(("qrz_error", (normalized, str(error))))

        Thread(
            target=worker,
            name=f"CarenDMR-QRZ-{normalized}",
            daemon=True,
        ).start()

    def _open_qrz_station(self) -> None:
        profile = self._qrz_profile
        if profile is None:
            return
        if self._qrz_window is not None:
            self._qrz_window.close()
        self._qrz_window = QrzStationWindow(
            profile,
            own_profile=self._qrz_own_profile,
            maptiler_api_key=self.qrz_service.maptiler_api_key,
            parent=self,
        )
        self.window_geometry.register("qrz_station", self._qrz_window)
        self._qrz_window.show()
        self._qrz_window.raise_()
        self._qrz_window.activateWindow()

    def _benchmark_reconnect(self) -> None:
        if not self.audio_benchmark_service.is_running:
            return
        if self.receive_service.is_running or self.receive_service.is_switching:
            return
        try:
            self.receive_service.set_receive_target(
                self.audio_benchmark_service.state.talkgroup,
                self.audio_benchmark_service.state.timeslot,
                "group",
            )
            self.receive_service.start()
        except Exception as error:
            self._updates.put(("benchmark_connection_lost", str(error)))

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
                    if bool(value):
                        self.statusBar().showMessage("Empfang wird gestartet …")
                    elif self.receive_service.is_running:
                        self.radio_state.synchronize(RadioState.CONNECTED)
                elif kind == "connect_error":
                    self.radio_state.synchronize(RadioState.ERROR)
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
        if state.connection is ConnectionState.CONNECTING:
            self.radio_state.synchronize(RadioState.CONNECTING)
        elif state.brandmeister_connected and state.receive_active:
            if not self._tx_active:
                self.radio_state.synchronize(RadioState.CONNECTED)
        elif state.connection is ConnectionState.ERROR:
            self.radio_state.synchronize(RadioState.ERROR)
        elif not state.receive_active and not self._tx_active and self.radio_state.state not in {RadioState.CONNECTING, RadioState.DISCONNECTING}:
            self.radio_state.synchronize(RadioState.DISCONNECTED)

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

    def _window_state_path(self) -> Path:
        return self.project_root / "config" / "window.local.json"

    def _restore_window_geometry(self) -> None:
        """Stellt Position/Größe wieder her, aber niemals unsichtbar off-screen."""
        path = self._window_state_path()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            encoded = str(payload.get("geometry", "")).strip()
            if not encoded:
                return
            raw = base64.b64decode(encoded.encode("ascii"))
            layout_version = int(payload.get("layout_version", 1) or 1)
            if not self.restoreGeometry(raw):
                return
            # 0.2.1.34 hat eine deutlich kompaktere Maske. Alte, für das vorherige
            # gestreckte Layout gespeicherte Größen werden einmalig normalisiert;
            # Position und alle künftig gespeicherten Größen bleiben erhalten.
            if layout_version < 2 and not self.isMaximized():
                self.resize(980, 720)
            app = QApplication.instance()
            screens = list(app.screens()) if app is not None else []
            frame = self.frameGeometry()
            visible = any(screen.availableGeometry().intersects(frame) for screen in screens)
            if not visible and screens:
                area = screens[0].availableGeometry()
                self.resize(min(self.width(), area.width()), min(self.height(), area.height()))
                self.move(area.center() - self.rect().center())
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return

    def _save_window_geometry(self) -> None:
        path = self._window_state_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "geometry": base64.b64encode(bytes(self.saveGeometry())).decode("ascii"),
                "maximized": bool(self.isMaximized()),
                "layout_version": 2,
            }
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except OSError:
            pass

    def closeEvent(self, event: QCloseEvent) -> None:
        self._save_window_geometry()
        self._tx_pending = False
        self._tx_elapsed_timer.stop()
        if self._tx_active and self._tx_stop_event is not None:
            self._tx_stop_event.set()
        if hasattr(self, "_channel_control_server"):
            self._channel_control_server.close()
        self.connection_manager.disconnect()
        self.receive_service.wait(3.0)
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
