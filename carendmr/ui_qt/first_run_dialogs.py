"""Barrierefreie Ersteinrichtung: Station und Sprach-Codec.

Beide Dialoge sind vollständig per Tastatur bedienbar. Jedes Eingabefeld hat
eine sichtbare Beschriftung (``setBuddy``) und einen zugänglichen Namen;
Fehler erscheinen als Meldungsfenster, das Screenreader sofort vorlesen.
Die Dialoge kennen keine Dateipfade der Konfiguration, sondern arbeiten nur
über ``StationSettingsService`` und ``CodecSetupService``.
"""
from __future__ import annotations

import queue
import threading
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from carendmr.application.codec_setup_service import (
    CORE_FILE,
    FIRMWARE_FILE,
    CodecSetupError,
    CodecSetupService,
    CodecState,
)
from carendmr.application.station_settings_service import StationSettingsService
from carendmr.ui_qt.accessibility import announce

CUSTOM_SERVER_LABEL = "Anderer Server …"


def _labeled(form: QFormLayout, text: str, widget: QWidget, accessible: str) -> None:
    label = QLabel(text)
    label.setBuddy(widget)
    widget.setAccessibleName(accessible)
    form.addRow(label, widget)


class StationSetupDialog(QDialog):
    """Rufzeichen, DMR-ID, Hotspot-Passwort und BrandMeister-Server."""

    def __init__(self, settings: StationSettingsService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self.setWindowTitle("CarenDMR – Station einrichten")
        self.setAccessibleName("Station einrichten")
        self.setModal(True)

        draft = settings.draft()
        layout = QVBoxLayout(self)
        intro = QLabel(
            "Willkommen bei CarenDMR. Bitte die Daten für die Anmeldung bei "
            "BrandMeister eintragen. Alle Angaben lassen sich später in den "
            "Einstellungen ändern."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form = QFormLayout()
        self.callsign_edit = QLineEdit(draft["callsign"])
        self.callsign_edit.setMaxLength(8)
        _labeled(form, "&Rufzeichen:", self.callsign_edit, "Rufzeichen")

        self.dmr_id_edit = QLineEdit(str(draft["dmr_id"]) if draft["dmr_id"] else "")
        _labeled(form, "&DMR-ID:", self.dmr_id_edit, "DMR-ID, nur Ziffern")

        self.password_edit = QLineEdit(draft["password"])
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        _labeled(
            form,
            "Hotspot-&Passwort:",
            self.password_edit,
            "BrandMeister Hotspot-Sicherheitspasswort",
        )

        self.server_combo = QComboBox()
        for master in settings.known_masters():
            self.server_combo.addItem(master.label, (master.host, master.port))
        self.server_combo.addItem(CUSTOM_SERVER_LABEL, None)
        _labeled(form, "&Server:", self.server_combo, "BrandMeister-Server")

        self.host_edit = QLineEdit(draft["host"])
        _labeled(form, "Server-&Adresse:", self.host_edit, "Adresse des BrandMeister-Servers")
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(int(draft["port"]))
        _labeled(form, "P&ort:", self.port_spin, "UDP-Port des BrandMeister-Servers")
        layout.addLayout(form)

        known = settings.find_master(draft["host"], int(draft["port"]))
        if known is not None:
            self.server_combo.setCurrentIndex(self.server_combo.findText(known.label))
        else:
            self.server_combo.setCurrentIndex(self.server_combo.count() - 1)
        self.server_combo.currentIndexChanged.connect(self._server_changed)
        self._server_changed()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("&Speichern")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Später")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.callsign_edit.setFocus()

    def _server_changed(self, *_args) -> None:
        data = self.server_combo.currentData()
        custom = data is None
        self.host_edit.setEnabled(custom)
        self.port_spin.setEnabled(custom)
        if not custom:
            host, port = data
            self.host_edit.setText(host)
            self.port_spin.setValue(int(port))

    def _save(self) -> None:
        dmr_text = self.dmr_id_edit.text().strip()
        if not dmr_text.isdigit():
            QMessageBox.warning(self, "CarenDMR", "Die DMR-ID darf nur aus Ziffern bestehen.")
            self.dmr_id_edit.setFocus()
            return
        try:
            self._settings.save_station(
                callsign=self.callsign_edit.text(),
                dmr_id=int(dmr_text),
                password=self.password_edit.text(),
                host=self.host_edit.text(),
                port=self.port_spin.value(),
            )
        except ValueError as error:
            QMessageBox.warning(self, "CarenDMR", str(error))
            return
        QMessageBox.information(self, "CarenDMR", "Die Stationsdaten wurden gespeichert.")
        self.accept()


class CodecSetupDialog(QDialog):
    """Sprach-Codec einrichten: Download oder eigene Dateien."""

    def __init__(self, codec: CodecSetupService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._codec = codec
        self._worker: threading.Thread | None = None
        self._messages: "queue.Queue[tuple[str, object]]" = queue.Queue()
        self.setWindowTitle("CarenDMR – Sprach-Codec einrichten")
        self.setAccessibleName("Sprach-Codec einrichten")
        self.setModal(True)

        layout = QVBoxLayout(self)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setAccessibleName("Status des Sprach-Codecs")
        layout.addWidget(self.status_label)

        info = QLabel(
            "CarenDMR verwendet für Sprache den Codec aus der Firmware des "
            "Funkgeräts MD380. Diese Firmware darf CarenDMR nicht mitliefern. "
            "Mit „Herunterladen“ holt CarenDMR die Original-Firmware 2.32 von "
            "md380.org und das passende RAM-Abbild aus dem Projekt md380tools, "
            "prüft beide anhand fester Prüfsummen und legt sie im eigenen "
            "Datenordner ab. Die Nutzung erfolgt in eigener Verantwortung."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self.download_button = QPushButton("&Herunterladen und einrichten")
        self.download_button.setAccessibleName("Herunterladen und einrichten")
        self.download_button.clicked.connect(self._start_download)
        layout.addWidget(self.download_button)

        manual = QLabel(
            "Ohne Internet: Firmware als Original-ZIP, als Update-Datei "
            f"MD-380-D2.32(AD).bin oder als {FIRMWARE_FILE} wählen, dazu {CORE_FILE}."
        )
        manual.setWordWrap(True)
        layout.addWidget(manual)

        form = QFormLayout()
        self.firmware_edit = QLineEdit()
        firmware_row, firmware_button = self._file_row(self.firmware_edit, "&Firmware wählen …")
        firmware_button.clicked.connect(
            lambda: self._choose(
                self.firmware_edit, "Firmware wählen",
                "Firmware (*.zip *.bin);;Alle Dateien (*)",
            )
        )
        _labeled(form, "Firmware-Datei:", self.firmware_edit, "Pfad zur Firmware-Datei")
        form.addRow("", firmware_row)

        self.core_edit = QLineEdit()
        core_row, core_button = self._file_row(self.core_edit, "&RAM-Abbild wählen …")
        core_button.clicked.connect(
            lambda: self._choose(self.core_edit, f"{CORE_FILE} wählen", "RAM-Abbild (*.img);;Alle Dateien (*)")
        )
        _labeled(form, f"RAM-Abbild ({CORE_FILE}):", self.core_edit, f"Pfad zur Datei {CORE_FILE}")
        form.addRow("", core_row)
        layout.addLayout(form)

        buttons = QDialogButtonBox()
        self.install_button = buttons.addButton("&Dateien übernehmen", QDialogButtonBox.ButtonRole.ApplyRole)
        self.close_button = buttons.addButton("Später", QDialogButtonBox.ButtonRole.RejectRole)
        self.install_button.clicked.connect(self._install)
        self.close_button.clicked.connect(self.reject)
        layout.addWidget(buttons)

        self._poll = QTimer(self)
        self._poll.setInterval(200)
        self._poll.timeout.connect(self._drain_messages)

        self._show_status()
        self.download_button.setFocus()

    @staticmethod
    def _file_row(edit: QLineEdit, button_text: str) -> tuple[QWidget, QPushButton]:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        button = QPushButton(button_text)
        button.setAccessibleName(button_text.replace("&", "").replace(" …", ""))
        row_layout.addWidget(button)
        row_layout.addStretch(1)
        return row, button

    def _choose(self, target: QLineEdit, title: str, filters: str) -> None:
        start = target.text().strip() or str(Path.home())
        path, _ = QFileDialog.getOpenFileName(self, title, start, filters)
        if path:
            target.setText(path)
            target.setFocus()

    def _set_busy(self, busy: bool) -> None:
        for widget in (self.download_button, self.install_button, self.firmware_edit, self.core_edit):
            widget.setEnabled(not busy)

    def _say(self, text: str) -> None:
        self.status_label.setText(text)
        announce(self.status_label, text)

    def _show_status(self) -> None:
        report = self._codec.status()
        self.status_label.setText(report.message)
        needs_files = report.state in (CodecState.FILES_MISSING, CodecState.READY_FILES)
        self.download_button.setEnabled(needs_files)
        self.install_button.setEnabled(needs_files)

    def _start_download(self) -> None:
        if self._worker is not None:
            return
        self._set_busy(True)
        self._say("Download gestartet. Bitte warten.")

        def work() -> None:
            try:
                report = self._codec.download_and_install(
                    progress=lambda text: self._messages.put(("progress", text))
                )
                self._messages.put(("done", report))
            except (CodecSetupError, OSError) as error:
                self._messages.put(("error", str(error)))

        self._worker = threading.Thread(target=work, name="CarenDMR-Codec-Download", daemon=True)
        self._worker.start()
        self._poll.start()

    def _drain_messages(self) -> None:
        while True:
            try:
                kind, payload = self._messages.get_nowait()
            except queue.Empty:
                return
            if kind == "progress":
                self._say(str(payload))
                continue
            self._poll.stop()
            self._worker = None
            self._set_busy(False)
            if kind == "error":
                self._show_status()
                QMessageBox.warning(self, "CarenDMR", str(payload))
                self.download_button.setFocus()
                return
            self._finish(payload)
            return

    def _finish(self, report) -> None:
        self._show_status()
        QMessageBox.information(self, "CarenDMR", report.message)
        if report.ready:
            self.accept()

    def _install(self) -> None:
        firmware = self.firmware_edit.text().strip()
        core = self.core_edit.text().strip()
        if not firmware or not core:
            QMessageBox.warning(self, "CarenDMR", "Bitte beide Dateien auswählen.")
            (self.firmware_edit if not firmware else self.core_edit).setFocus()
            return
        try:
            report = self._codec.install_files(Path(firmware), Path(core))
        except (CodecSetupError, OSError) as error:
            QMessageBox.warning(self, "CarenDMR", str(error))
            return
        self._finish(report)

    def reject(self) -> None:
        if self._worker is not None:
            self._say("Der Download läuft noch. Bitte kurz warten.")
            return
        super().reject()


def run_first_run_setup(services, parent: QWidget | None = None) -> None:
    """Zeigt fehlende Einrichtungsschritte vor dem ersten Fenster.

    ``services`` ist ein ``FirstRunServices`` aus ``carendmr.bootstrap``.
    Abbrechen ist erlaubt; CarenDMR startet dann trotzdem.
    """
    if services.station_settings.needs_setup():
        StationSetupDialog(services.station_settings, parent).exec()
    if services.codec_setup.status().state is CodecState.FILES_MISSING:
        CodecSetupDialog(services.codec_setup, parent).exec()
