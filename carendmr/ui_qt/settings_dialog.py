"""Separates Qt-Einstellungsfenster für CarenDMR.

Die erste Stufe portiert die im Funkbetrieb relevanten lokalen Audio- und
Diagnoseeinstellungen. Änderungen werden erst mit »Übernehmen« oder »OK«
gespeichert.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QGridLayout,
    QKeySequenceEdit,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QTabWidget, QWidget, QFileDialog, QApplication,
)

from carendmr.ui_qt.theme import METRICS
from carendmr.audio import AudioDirection
from carendmr.diagnostics import initialize as initialize_diagnostics
from carendmr.diagnostics import set_enabled as set_diagnostics_enabled
from carendmr.accessibility.hotkeys import DEFAULT_HOTKEYS, FUNCTION_LABELS, HotkeyManager
from carendmr.application import ContactService, EncoderService
from carendmr.brandmeister.config import BrandMeisterConfigStore


class SettingsDialog(QDialog):
    """Lokale Audio- und Diagnoseeinstellungen als eigenes Fenster."""

    settings_applied = Signal()

    def __init__(self, project_root: Path, audio_service, receive_service, parent=None) -> None:
        super().__init__(parent)
        self.project_root = Path(project_root)
        self.audio_service = audio_service
        self.receive_service = receive_service
        self._input_devices = []
        self._output_devices = []
        self.hotkey_manager = HotkeyManager(self.project_root / "config" / "hotkeys.local.json")
        self.contact_service = ContactService(self.project_root)
        self.encoder_service = EncoderService(self.project_root)
        self._pending_hotkeys = self.hotkey_manager.mapping
        self._selected_function: str | None = None

        self.setWindowTitle("CarenDMR – Einstellungen")
        self.setMinimumSize(680, 520)
        self.resize(780, 820)
        self._build_ui()
        self._load_devices()
        self._load_values()
        self._load_profile_and_system_info()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        heading = QLabel("Einstellungen")
        heading.setObjectName("dialogTitle")
        font = heading.font()
        font.setPointSize(18)
        font.setBold(True)
        heading.setFont(font)
        root.addWidget(heading)
        root.addWidget(QLabel("Thematisch gegliederte CarenDMR-Einstellungen. Änderungen werden mit Übernehmen oder OK gespeichert."))

        self.tabs = QTabWidget(self)
        root.addWidget(self.tabs, 1)

        # Audio
        audio_page = QWidget()
        audio_root = QVBoxLayout(audio_page)
        audio_box = QGroupBox("Audiogeräte und Pegel")
        audio_form = QFormLayout(audio_box)
        microphone_row = QHBoxLayout()
        self.microphone_combo = QComboBox()
        self.rescan_button = QPushButton("Neu einlesen")
        self.rescan_button.clicked.connect(self._load_devices)
        microphone_row.addWidget(self.microphone_combo, 1)
        microphone_row.addWidget(self.rescan_button)
        audio_form.addRow("Mikrofon:", microphone_row)
        self.output_combo = QComboBox()
        audio_form.addRow("Wiedergabegerät:", self.output_combo)
        gain_row = QHBoxLayout()
        self.gain_slider = QSlider(Qt.Orientation.Horizontal); self.gain_slider.setRange(0, 100)
        self.gain_value = QLabel("100 %"); self.gain_value.setMinimumWidth(58)
        self.gain_slider.valueChanged.connect(lambda v: self.gain_value.setText(f"{v} %"))
        gain_row.addWidget(self.gain_slider, 1); gain_row.addWidget(self.gain_value)
        audio_form.addRow("Mic-Gain:", gain_row)
        volume_row = QHBoxLayout()
        self.volume_slider = QSlider(Qt.Orientation.Horizontal); self.volume_slider.setRange(0, 400)
        self.volume_value = QLabel("100 %"); self.volume_value.setMinimumWidth(58)
        self.volume_slider.valueChanged.connect(lambda v: self.volume_value.setText(f"{v} %"))
        volume_row.addWidget(self.volume_slider, 1); volume_row.addWidget(self.volume_value)
        audio_form.addRow("RX-Pegel / Zusatzverstärkung:", volume_row)
        self.muted_check = QCheckBox("Empfang stummschalten")
        self.agc_check = QCheckBox("Automatische Lautstärkeanpassung (AGC)")
        audio_form.addRow("", self.muted_check); audio_form.addRow("", self.agc_check)
        audio_root.addWidget(audio_box); audio_root.addStretch(1)
        self.tabs.addTab(audio_page, "Audio")

        # Netzwerk
        network_page = QWidget(); network_root = QVBoxLayout(network_page)
        network_box = QGroupBox("BrandMeister-Profil")
        network_form = QFormLayout(network_box)
        self.network_server = QLabel("Nicht konfiguriert")
        self.network_callsign = QLabel("—")
        self.network_dmr_id = QLabel("—")
        self.network_port = QLabel("62031")
        self.network_location = QLabel("—")
        network_form.addRow("Server:", self.network_server)
        network_form.addRow("Rufzeichen:", self.network_callsign)
        network_form.addRow("DMR-ID:", self.network_dmr_id)
        network_form.addRow("Port:", self.network_port)
        network_form.addRow("Standort:", self.network_location)
        note = QLabel("Zugangsdaten werden weiterhin ausschließlich in config/brandmeister.local.json verwaltet.")
        note.setWordWrap(True)
        network_root.addWidget(network_box); network_root.addWidget(note); network_root.addStretch(1)
        self.tabs.addTab(network_page, "Netzwerk")

        # Datenbanken
        data_page = QWidget(); data_root = QVBoxLayout(data_page)
        contacts_box = QGroupBox("RadioID-Kontaktdaten")
        contacts_layout = QVBoxLayout(contacts_box)
        self.contacts_status = QLabel("Kontaktdatenbank wird geprüft …"); self.contacts_status.setWordWrap(True)
        self.contacts_update_button = QPushButton("Kontaktdaten aktualisieren")
        self.contacts_update_button.clicked.connect(self._update_contacts)
        contacts_layout.addWidget(self.contacts_status); contacts_layout.addWidget(self.contacts_update_button, 0, Qt.AlignmentFlag.AlignLeft)
        qso_box = QGroupBox("QSO-Datenbank")
        qso_form = QFormLayout(qso_box)
        self.qso_path_label = QLabel(str(self.project_root / "data" / "qso_history.db")); self.qso_path_label.setWordWrap(True)
        self.qso_status_label = QLabel("Lokale SQLite-Historie")
        qso_form.addRow("Pfad:", self.qso_path_label); qso_form.addRow("Status:", self.qso_status_label)
        data_root.addWidget(contacts_box); data_root.addWidget(qso_box); data_root.addStretch(1)
        self.tabs.addTab(data_page, "Datenbanken")

        # Codec / Decoder
        codec_page = QWidget(); codec_root = QVBoxLayout(codec_page)
        codec_box = QGroupBox("AMBE-Codec")
        codec_form = QFormLayout(codec_box)
        self.encoder_backend_label = QLabel("Noch nicht geprüft")
        self.encoder_plugin_label = QLabel("Nicht zugeordnet"); self.encoder_plugin_label.setWordWrap(True)
        self.encoder_message_label = QLabel("—"); self.encoder_message_label.setWordWrap(True)
        codec_form.addRow("Encoder/Decoder:", self.encoder_backend_label)
        codec_form.addRow("Plugin:", self.encoder_plugin_label)
        codec_form.addRow("Prüfergebnis:", self.encoder_message_label)
        codec_buttons = QHBoxLayout()
        self.encoder_select_button = QPushButton("Plugin zuordnen")
        self.encoder_verify_button = QPushButton("Erneut prüfen")
        self.encoder_select_button.clicked.connect(self._select_encoder_plugin)
        self.encoder_verify_button.clicked.connect(self._verify_encoder_plugin)
        codec_buttons.addWidget(self.encoder_select_button); codec_buttons.addWidget(self.encoder_verify_button); codec_buttons.addStretch(1)
        codec_root.addWidget(codec_box); codec_root.addLayout(codec_buttons); codec_root.addStretch(1)
        self.tabs.addTab(codec_page, "Codec / Decoder")

        # Diagnose
        diag_page = QWidget(); diag_root = QVBoxLayout(diag_page)
        diag_box = QGroupBox("Diagnose")
        diag_layout = QVBoxLayout(diag_box)
        self.diagnostics_check = QCheckBox("Diagnosemodus aktiv")
        self.audio_debug_check = QCheckBox("Audio-Diagnose als WAV speichern")
        self.log_path_label = QLabel(f"Logverzeichnis: {self.project_root / 'logs'}"); self.log_path_label.setWordWrap(True)
        diag_layout.addWidget(self.diagnostics_check); diag_layout.addWidget(self.audio_debug_check); diag_layout.addWidget(self.log_path_label)
        diag_root.addWidget(diag_box); diag_root.addStretch(1)
        self.tabs.addTab(diag_page, "Diagnose")

        # Hotkeys
        hotkey_page = QWidget(); hotkey_root = QVBoxLayout(hotkey_page)
        self.hotkey_table = QTableWidget(len(DEFAULT_HOTKEYS), 2)
        self.hotkey_table.setHorizontalHeaderLabels(["Funktion", "Aktuelle Taste"])
        self.hotkey_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.hotkey_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.hotkey_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.hotkey_table.setTabKeyNavigation(False); self.hotkey_table.verticalHeader().setVisible(False); self.hotkey_table.verticalHeader().setDefaultSectionSize(METRICS.table_row_height)
        self.hotkey_table.horizontalHeader().setStretchLastSection(True)
        for row, function in enumerate(DEFAULT_HOTKEYS):
            item = QTableWidgetItem(FUNCTION_LABELS[function]); item.setData(Qt.ItemDataRole.UserRole, function)
            self.hotkey_table.setItem(row, 0, item)
            self.hotkey_table.setItem(row, 1, QTableWidgetItem(self._display_hotkey(self._pending_hotkeys.get(function, ""))))
        hotkey_root.addWidget(self.hotkey_table)
        capture_form = QFormLayout()
        self.current_hotkey_label = QLabel("Keine Funktion ausgewählt")
        self.hotkey_capture = QKeySequenceEdit(); self.hotkey_capture.setMaximumSequenceLength(1); self.hotkey_capture.setClearButtonEnabled(True)
        self.hotkey_capture.keySequenceChanged.connect(self._hotkey_sequence_changed)
        self.hotkey_status = QLabel("Bitte zuerst eine Funktion auswählen."); self.hotkey_status.setWordWrap(True)
        capture_form.addRow("Ausgewählte Funktion:", self.current_hotkey_label)
        capture_form.addRow("Neue Tastenkombination drücken:", self.hotkey_capture)
        capture_form.addRow("Status:", self.hotkey_status)
        hotkey_root.addLayout(capture_form)
        hotkey_buttons = QHBoxLayout()
        self.assign_hotkey_button = QPushButton("Zuweisen"); self.assign_hotkey_button.clicked.connect(self._assign_hotkey)
        self.remove_hotkey_button = QPushButton("Zuordnung entfernen"); self.remove_hotkey_button.clicked.connect(self._remove_hotkey)
        self.reset_hotkeys_button = QPushButton("Werkseinstellungen"); self.reset_hotkeys_button.clicked.connect(self._reset_hotkeys)
        hotkey_buttons.addWidget(self.assign_hotkey_button); hotkey_buttons.addWidget(self.remove_hotkey_button); hotkey_buttons.addStretch(1); hotkey_buttons.addWidget(self.reset_hotkeys_button)
        hotkey_root.addLayout(hotkey_buttons)
        self.tabs.addTab(hotkey_page, "Hotkeys")

        # Erst verbinden und auswählen, wenn alle Ziel-Widgets existieren.
        self.hotkey_table.itemSelectionChanged.connect(self._hotkey_selection_changed)
        if self.hotkey_table.rowCount():
            self.hotkey_table.selectRow(0)

        self.status_label = QLabel("Bereit"); self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self._accept); self.buttons.rejected.connect(self.reject)
        apply_button = self.buttons.button(QDialogButtonBox.StandardButton.Apply)
        if apply_button is not None: apply_button.clicked.connect(self._apply)
        root.addWidget(self.buttons)
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self._apply)

    def _load_profile_and_system_info(self) -> None:
        try:
            cfg = BrandMeisterConfigStore(self.project_root / "config" / "brandmeister.local.json").load()
            self.network_server.setText(cfg.host); self.network_callsign.setText(cfg.callsign)
            self.network_dmr_id.setText(str(cfg.dmr_id)); self.network_port.setText(str(cfg.port))
            self.network_location.setText(cfg.location or "—")
        except Exception as exc:
            self.network_server.setText(f"Nicht verfügbar: {exc}")
        try:
            info = self.contact_service.info()
            count = getattr(info, "record_count", 0)
            updated = getattr(info, "updated_at", "")
            self.contacts_status.setText(f"{count} Kontakte; Stand {updated or 'unbekannt'}; Datei {self.contact_service.database_path}")
        except Exception:
            self.contacts_status.setText(f"Keine nutzbare Kontaktdatenbank gefunden: {self.contact_service.database_path}")
        self._verify_encoder_plugin()

    def _update_contacts(self) -> None:
        self.contacts_update_button.setEnabled(False)
        self.contacts_update_button.setText("Aktualisierung läuft …")
        message = "Kontaktdaten werden aktualisiert … Bitte warten."
        self.contacts_status.setText(message)
        self.status_label.setText(message)
        QApplication.processEvents()
        try:
            count, updated = self.contact_service.update()
            result = f"Aktualisierung erfolgreich: {count} Kontakte; Stand {updated}; Datei {self.contact_service.database_path}"
            self.contacts_status.setText(result)
            self.status_label.setText("Kontaktdaten wurden aktualisiert.")
        except Exception as exc:
            error = f"Aktualisierung fehlgeschlagen: {exc}"
            self.contacts_status.setText(error)
            self.status_label.setText(error)
            QMessageBox.critical(self, "Kontaktdaten", str(exc))
        finally:
            self.contacts_update_button.setText("Kontaktdaten aktualisieren")
            self.contacts_update_button.setEnabled(True)

    def _select_encoder_plugin(self) -> None:
        start_dir = self.project_root / "plugins"
        if not start_dir.is_dir():
            start_dir = self.project_root
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Vocoder-Plugin auswählen",
            str(start_dir),
            "Vocoder-Plugins (vocoder_plugin* *.dll *.so *.dylib);;Alle Dateien (*.* *)",
        )
        if not path: return
        try:
            diag = self.encoder_service.configure_and_verify(Path(path))
            self._show_encoder_diagnostics(diag)
            self.status_label.setText("Vocoder-Plugin wurde zugeordnet und geprüft.")
        except Exception as exc:
            QMessageBox.critical(self, "Codec / Decoder", str(exc))
            self.encoder_message_label.setText(str(exc))

    def _verify_encoder_plugin(self) -> None:
        plugin = self.encoder_service.detect_plugin()
        self.encoder_plugin_label.setText(str(plugin) if plugin else "Nicht zugeordnet")
        try:
            if plugin is None:
                raise RuntimeError("Kein Vocoder-Plugin gefunden. Bitte Plugin zuordnen.")
            if self.encoder_service.configured_plugin_path != plugin:
                diag = self.encoder_service.configure_and_verify(plugin)
                self.status_label.setText(f"Vocoder-Plugin automatisch erkannt: {plugin.name}")
            else:
                diag = self.encoder_service.verify_configured()
            self._show_encoder_diagnostics(diag)
        except Exception as exc:
            self.encoder_backend_label.setText("Nicht bereit")
            self.encoder_message_label.setText(str(exc))

    def _show_encoder_diagnostics(self, diag) -> None:
        self.encoder_backend_label.setText(f"{diag.backend} – {'bereit' if diag.ready else 'nicht bereit'}")
        self.encoder_plugin_label.setText(diag.plugin_path)
        self.encoder_message_label.setText(diag.message)

    def _load_devices(self) -> None:
        self.status_label.setText("Audiogeräte werden eingelesen …")
        try:
            manager = self.audio_service.manager
            manager.scan()
            self._input_devices = list(manager.list_devices(AudioDirection.INPUT))
            self._output_devices = list(manager.list_devices(AudioDirection.OUTPUT))

            self.microphone_combo.clear()
            for device in self._input_devices:
                self.microphone_combo.addItem(device.display_name(AudioDirection.INPUT), device.stable_key)

            self.output_combo.clear()
            for device in self._output_devices:
                self.output_combo.addItem(device.display_name(AudioDirection.OUTPUT), device.stable_key)

            self._select_resolved_devices()
            self.status_label.setText(
                f"{len(self._input_devices)} Mikrofon(e) und {len(self._output_devices)} Wiedergabegerät(e) gefunden."
            )
        except Exception as exc:
            self.status_label.setText(f"Audiogeräte konnten nicht eingelesen werden: {exc}")

    def _select_resolved_devices(self) -> None:
        manager = self.audio_service.manager
        try:
            selected_input = manager.resolve(AudioDirection.INPUT).device
            self._select_combo_key(self.microphone_combo, selected_input.stable_key)
        except Exception:
            pass
        try:
            selected_output = manager.resolve(AudioDirection.OUTPUT).device
            self._select_combo_key(self.output_combo, selected_output.stable_key)
        except Exception:
            pass

    @staticmethod
    def _select_combo_key(combo: QComboBox, stable_key: str) -> None:
        index = combo.findData(stable_key)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _load_values(self) -> None:
        self.gain_slider.setValue(int(self.audio_service.gain_percent))
        self.volume_slider.setValue(int(self.audio_service.output_volume_percent))
        self.muted_check.setChecked(bool(self.audio_service.user_muted))
        self.agc_check.setChecked(bool(self.audio_service.agc_enabled))
        self.audio_debug_check.setChecked(bool(self.audio_service.audio_debug_wav_enabled))
        self.diagnostics_check.setChecked(bool(initialize_diagnostics(self.project_root)))

    def _device_by_key(self, devices, stable_key: str):
        return next((device for device in devices if device.stable_key == stable_key), None)

    @staticmethod
    def _display_hotkey(value: str) -> str:
        return value or "Nicht zugeordnet"

    @staticmethod
    def _reserved_reason(sequence: str) -> str | None:
        normalized = sequence.strip()
        if not normalized:
            return "Keine Tastenkombination erfasst."
        blocked = {
            "Tab", "Backtab", "Return", "Enter", "Esc", "Escape", "Backspace", "Delete",
            "Left", "Right", "Up", "Down", "Home", "End", "PageUp", "PageDown",
            "Ctrl+C", "Ctrl+V", "Ctrl+X", "Ctrl+A", "Alt+F4",
        }
        if normalized in blocked:
            return f"{normalized} ist für Navigation, Bearbeitung oder das Betriebssystem reserviert."
        if len(normalized) == 1 and normalized.isalnum():
            return "Einzelne Buchstaben und Ziffern sind nicht zulässig. Bitte eine Funktionstaste oder eine Kombination verwenden."
        return None

    def _refresh_hotkey_table(self) -> None:
        for row, function in enumerate(DEFAULT_HOTKEYS):
            self.hotkey_table.item(row, 1).setText(self._display_hotkey(self._pending_hotkeys.get(function, "")))

    def _hotkey_selection_changed(self) -> None:
        # Qt kann die Auswahl bereits während des Dialogaufbaus melden.
        if not hasattr(self, "current_hotkey_label"):
            return
        items = self.hotkey_table.selectedItems()
        if not items:
            self._selected_function = None
            self.current_hotkey_label.setText("Keine Funktion ausgewählt")
            return
        row = items[0].row()
        function = self.hotkey_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self._selected_function = str(function)
        current = self._pending_hotkeys.get(self._selected_function, "")
        self.current_hotkey_label.setText(f"{FUNCTION_LABELS[self._selected_function]} – {self._display_hotkey(current)}")
        self.hotkey_capture.clear()
        self.hotkey_status.setText("Neue Tastenkombination drücken oder die bestehende Zuordnung entfernen.")

    def _hotkey_sequence_changed(self, sequence: QKeySequence) -> None:
        text = sequence.toString(QKeySequence.SequenceFormat.PortableText)
        reason = self._reserved_reason(text)
        if reason:
            self.hotkey_status.setText(reason)
            return
        conflict = next((fn for fn, key in self._pending_hotkeys.items()
                         if fn != self._selected_function and key.lower() == text.lower()), None)
        if conflict:
            self.hotkey_status.setText(f"{text} ist bereits für {FUNCTION_LABELS[conflict]} vergeben. Beim Zuweisen kann die alte Zuordnung gelöst werden.")
        else:
            self.hotkey_status.setText(f"{text} ist frei.")

    def _assign_hotkey(self) -> None:
        if not self._selected_function:
            self.hotkey_status.setText("Bitte zuerst eine Funktion auswählen.")
            return
        value = self.hotkey_capture.keySequence().toString(QKeySequence.SequenceFormat.PortableText)
        reason = self._reserved_reason(value)
        if reason:
            self.hotkey_status.setText(reason)
            return
        conflict = next((fn for fn, key in self._pending_hotkeys.items()
                         if fn != self._selected_function and key.lower() == value.lower()), None)
        if conflict:
            answer = QMessageBox.question(
                self, "Tastenkombination neu zuordnen",
                f"{value} ist bereits für {FUNCTION_LABELS[conflict]} vergeben.\n\n"
                f"Soll die alte Zuordnung entfernt und {FUNCTION_LABELS[self._selected_function]} zugewiesen werden?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            self._pending_hotkeys[conflict] = ""
        self._pending_hotkeys[self._selected_function] = value
        self._refresh_hotkey_table()
        self.current_hotkey_label.setText(f"{FUNCTION_LABELS[self._selected_function]} – {value}")
        self.hotkey_status.setText(f"{value} wurde vorgemerkt. Mit Übernehmen oder OK speichern.")
        self.hotkey_capture.clear()

    def _remove_hotkey(self) -> None:
        if not self._selected_function:
            self.hotkey_status.setText("Bitte zuerst eine Funktion auswählen.")
            return
        self._pending_hotkeys[self._selected_function] = ""
        self._refresh_hotkey_table()
        self.current_hotkey_label.setText(f"{FUNCTION_LABELS[self._selected_function]} – Nicht zugeordnet")
        self.hotkey_status.setText("Zuordnung wurde vorgemerkt. Mit Übernehmen oder OK speichern.")
        self.hotkey_capture.clear()

    def _reset_hotkeys(self) -> None:
        answer = QMessageBox.question(
            self,
            "Werkseinstellungen wiederherstellen",
            "Alle Tastenkürzel auf die Werkseinstellungen zurücksetzen?\n\n"
            "Die Änderung wird erst mit Übernehmen oder OK gespeichert.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            self.hotkey_status.setText("Zurücksetzen wurde abgebrochen.")
            return

        self._pending_hotkeys = dict(DEFAULT_HOTKEYS)
        self._refresh_hotkey_table()
        self.hotkey_capture.clear()
        self.hotkey_status.setText("Werkseinstellungen wurden vorgemerkt. Mit Übernehmen oder OK speichern.")
        self.status_label.setText("Hotkeys wurden auf Werkseinstellungen vorgemerkt.")

    def _save_hotkeys(self) -> None:
        normalized: dict[str, str] = {}
        used: dict[str, str] = {}
        for function in DEFAULT_HOTKEYS:
            value = HotkeyManager.normalize_key(self._pending_hotkeys.get(function, ""))
            if value:
                key = value.lower()
                if key in used:
                    raise ValueError(
                        f"{value} ist doppelt belegt: {FUNCTION_LABELS[used[key]]} und {FUNCTION_LABELS[function]}."
                    )
                used[key] = function
            normalized[function] = value
        self.hotkey_manager._mapping = normalized
        self.hotkey_manager.save()

    def _apply(self) -> bool:
        try:
            input_key = str(self.microphone_combo.currentData() or "")
            output_key = str(self.output_combo.currentData() or "")
            input_device = self._device_by_key(self._input_devices, input_key)
            output_device = self._device_by_key(self._output_devices, output_key)
            if input_device is None:
                raise ValueError("Bitte ein verfügbares Mikrofon auswählen.")
            if output_device is None:
                raise ValueError("Bitte ein verfügbares Wiedergabegerät auswählen.")

            self.audio_service.manager.save_selection(input_device, output_device)
            self.audio_service.select_microphone(input_device.stable_key)
            self.audio_service.set_gain_percent(self.gain_slider.value())
            self.audio_service.set_output_volume_percent(self.volume_slider.value())
            self.audio_service.set_user_muted(self.muted_check.isChecked())
            self.audio_service.set_agc_enabled(self.agc_check.isChecked())
            self.audio_service.set_audio_debug_wav_enabled(self.audio_debug_check.isChecked())
            self.audio_service.save_settings()
            self._save_hotkeys()

            self.receive_service.set_output_volume_percent(self.audio_service.output_volume_percent)
            self.receive_service.set_user_muted(self.audio_service.user_muted)
            self.receive_service.set_agc_enabled(self.audio_service.agc_enabled)
            set_diagnostics_enabled(self.diagnostics_check.isChecked())

            self.status_label.setText("Einstellungen wurden gespeichert und übernommen.")
            self.settings_applied.emit()
            return True
        except Exception as exc:
            QMessageBox.critical(self, "Einstellungen", str(exc))
            self.status_label.setText(f"Fehler: {exc}")
            return False

    def _accept(self) -> None:
        if self._apply():
            self.accept()
