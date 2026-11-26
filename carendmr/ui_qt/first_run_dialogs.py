"""Barrierefreie Ersteinrichtung: Station, Sprach-Codec, Audio, Kontakte.

Alle Dialoge sind vollständig per Tastatur bedienbar. Jedes Eingabefeld hat
eine sichtbare Beschriftung (``setBuddy``) und einen zugänglichen Namen;
Fehler erscheinen als Meldungsfenster, das Screenreader sofort vorlesen.
Netzwerkzugriffe (Verbindungstest, Downloads) laufen in Hintergrund-Threads;
der Fortschritt wird angesagt. Die Dialoge arbeiten nur über Dienste aus
``carendmr.application`` und kennen keine Konfigurationsdateien.
"""
from __future__ import annotations

import queue
import threading
from pathlib import Path
from typing import Callable

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
    SETUP_HINT,
    CodecSetupError,
    CodecSetupService,
    CodecState,
)
from carendmr.application.station_settings_service import (
    StationSettingsService,
    locator_to_latlon,
)
from carendmr.ui_qt.accessibility import announce

CUSTOM_SERVER_LABEL = "Anderer Server …"
SERVER_LOCKED_HINT = (
    "Adresse und Port sind durch die Serverauswahl festgelegt. "
    "Zum Ändern bei Server „Anderer Server …“ wählen."
)


def _labeled(form: QFormLayout, text: str, widget: QWidget, accessible: str) -> None:
    label = QLabel(text)
    label.setBuddy(widget)
    widget.setAccessibleName(accessible)
    form.addRow(label, widget)


def _parse_float(text: str, what: str) -> float:
    try:
        return float(text.strip().replace(",", "."))
    except ValueError as error:
        raise ValueError(f"{what} muss eine Zahl sein, zum Beispiel 52,31.") from error


class _Background:
    """Führt eine Funktion im Hintergrund aus und meldet im GUI-Thread zurück."""

    def __init__(self, owner: QWidget) -> None:
        self._queue: "queue.Queue[tuple[str, object]]" = queue.Queue()
        self._thread: threading.Thread | None = None
        self._on_done: Callable[[object], None] | None = None
        self._on_error: Callable[[Exception], None] | None = None
        self._on_progress: Callable[[str], None] | None = None
        self._timer = QTimer(owner)
        self._timer.setInterval(150)
        self._timer.timeout.connect(self._drain)

    @property
    def busy(self) -> bool:
        return self._thread is not None

    def start(self, work, *, on_done, on_error, on_progress=None, name="CarenDMR-Einrichtung") -> None:
        if self._thread is not None:
            return
        self._on_done, self._on_error, self._on_progress = on_done, on_error, on_progress

        def run() -> None:
            try:
                result = work(lambda text: self._queue.put(("progress", text)))
                self._queue.put(("done", result))
            except Exception as error:  # Meldung im GUI-Thread anzeigen
                self._queue.put(("error", error))

        self._thread = threading.Thread(target=run, name=name, daemon=True)
        self._thread.start()
        self._timer.start()

    def _drain(self) -> None:
        while True:
            try:
                kind, payload = self._queue.get_nowait()
            except queue.Empty:
                return
            if kind == "progress":
                if self._on_progress is not None:
                    self._on_progress(str(payload))
                continue
            self._timer.stop()
            self._thread = None
            if kind == "done":
                self._on_done(payload)
            else:
                self._on_error(payload)  # type: ignore[arg-type]
            return


class StationSetupDialog(QDialog):
    """Rufzeichen, DMR-ID, Passwort, Standort und Server – mit Verbindungstest."""

    def __init__(
        self,
        settings: StationSettingsService,
        parent: QWidget | None = None,
        *,
        connection_active: Callable[[], bool] | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        self._connection_active = connection_active or (lambda: False)
        self._tested_ok = False
        self._background = _Background(self)
        self.setWindowTitle("CarenDMR – Station einrichten")
        self.setAccessibleName("Station einrichten")
        self.setModal(True)

        draft = settings.draft()
        layout = QVBoxLayout(self)
        intro = QLabel(
            "Bitte die Daten für die Anmeldung bei BrandMeister eintragen und "
            "mit „Verbindung testen“ prüfen. Der Test meldet sich einmal an und "
            "wieder ab, ohne zu senden. Alle Angaben lassen sich später ändern."
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
            form, "Hotspot-&Passwort:", self.password_edit,
            "BrandMeister Hotspot-Sicherheitspasswort",
        )

        self.locator_edit = QLineEdit(draft["location"])
        self.locator_edit.setMaxLength(6)
        _labeled(form, "&Locator:", self.locator_edit, "Maidenhead-Locator, zum Beispiel JO52FI")
        self.latitude_edit = QLineEdit(self._number_text(draft["latitude"]))
        _labeled(form, "&Breitengrad:", self.latitude_edit, "Breitengrad in Grad, Norden positiv")
        self.longitude_edit = QLineEdit(self._number_text(draft["longitude"]))
        _labeled(form, "Län&gengrad:", self.longitude_edit, "Längengrad in Grad, Osten positiv")
        self.locator_edit.editingFinished.connect(self._locator_changed)

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
        self.server_hint = QLabel(SERVER_LOCKED_HINT)
        self.server_hint.setWordWrap(True)
        self.server_hint.setAccessibleName("Hinweis zu Adresse und Port")
        form.addRow("", self.server_hint)
        layout.addLayout(form)

        known = settings.find_master(draft["host"], int(draft["port"]))
        if known is not None:
            self.server_combo.setCurrentIndex(self.server_combo.findText(known.label))
        else:
            self.server_combo.setCurrentIndex(self.server_combo.count() - 1)
        self.server_combo.currentIndexChanged.connect(self._server_changed)
        self._server_changed()

        self.status_label = QLabel("Noch nicht getestet.")
        self.status_label.setWordWrap(True)
        self.status_label.setAccessibleName("Ergebnis des Verbindungstests")
        layout.addWidget(self.status_label)

        buttons = QDialogButtonBox()
        self.test_button = buttons.addButton("Verbindung &testen", QDialogButtonBox.ButtonRole.ActionRole)
        self.save_button = buttons.addButton("&Speichern", QDialogButtonBox.ButtonRole.AcceptRole)
        self.later_button = buttons.addButton("Später", QDialogButtonBox.ButtonRole.RejectRole)
        self.test_button.clicked.connect(self._test)
        self.save_button.clicked.connect(self._save)
        self.later_button.clicked.connect(self.reject)
        layout.addWidget(buttons)

        for edit in (self.callsign_edit, self.dmr_id_edit, self.password_edit, self.host_edit):
            edit.textEdited.connect(self._inputs_changed)
        self.port_spin.valueChanged.connect(self._inputs_changed)
        self.server_combo.currentIndexChanged.connect(self._inputs_changed)

        if self._connection_active():
            self.test_button.setEnabled(False)
            self.status_label.setText(
                "CarenDMR ist gerade verbunden. Für einen Verbindungstest zuerst trennen. "
                "Gespeicherte Änderungen gelten beim nächsten Verbinden."
            )
        self.callsign_edit.setFocus()

    @staticmethod
    def _number_text(value: float) -> str:
        return "" if not value else f"{value:g}".replace(".", ",")

    def _say(self, text: str) -> None:
        self.status_label.setText(text)
        announce(self.status_label, text)

    def _inputs_changed(self, *_args) -> None:
        if self._tested_ok:
            self._tested_ok = False
            self.status_label.setText("Eingaben geändert – bitte erneut testen.")

    def _locator_changed(self) -> None:
        text = self.locator_edit.text().strip().upper()
        self.locator_edit.setText(text)
        if not text:
            return
        try:
            latitude, longitude = locator_to_latlon(text)
        except ValueError as error:
            self._say(str(error))
            return
        self.latitude_edit.setText(self._number_text(latitude))
        self.longitude_edit.setText(self._number_text(longitude))
        self._say(
            f"Koordinaten aus dem Locator übernommen: Breite {self.latitude_edit.text()}, "
            f"Länge {self.longitude_edit.text()}. Bei Bedarf genauer eintragen."
        )

    def _server_changed(self, *_args) -> None:
        data = self.server_combo.currentData()
        custom = data is None
        self.host_edit.setEnabled(custom)
        self.port_spin.setEnabled(custom)
        self.server_hint.setVisible(not custom)
        # Gesperrte Felder sind per Tab nicht erreichbar; der Hinweis hängt
        # deshalb auch an der Serverauswahl und wird dort mit angesagt.
        self.server_combo.setAccessibleDescription("" if custom else SERVER_LOCKED_HINT)
        if not custom:
            host, port = data
            self.host_edit.setText(host)
            self.port_spin.setValue(int(port))

    def _values(self) -> dict:
        dmr_text = self.dmr_id_edit.text().strip()
        if not dmr_text.isdigit():
            self.dmr_id_edit.setFocus()
            raise ValueError("Die DMR-ID darf nur aus Ziffern bestehen.")
        locator = self.locator_edit.text().strip().upper()
        if locator:
            locator_to_latlon(locator)  # prüft das Format
        latitude = _parse_float(self.latitude_edit.text() or "0", "Der Breitengrad")
        longitude = _parse_float(self.longitude_edit.text() or "0", "Der Längengrad")
        return {
            "callsign": self.callsign_edit.text(),
            "dmr_id": int(dmr_text),
            "password": self.password_edit.text(),
            "host": self.host_edit.text(),
            "port": self.port_spin.value(),
            "location": locator,
            "latitude": latitude,
            "longitude": longitude,
        }

    def _set_busy(self, busy: bool) -> None:
        for widget in (self.test_button, self.save_button):
            widget.setEnabled(not busy)
        if busy is False and self._connection_active():
            self.test_button.setEnabled(False)

    def _test(self) -> None:
        if self._background.busy:
            return
        try:
            config = self._settings.build_config(**self._values())
        except ValueError as error:
            QMessageBox.warning(self, "CarenDMR", str(error))
            return
        self._set_busy(True)
        self._say(f"Verbindungstest mit {config.host} läuft. Bitte warten.")
        self._background.start(
            lambda _progress: self._settings.test_login(config),
            on_done=self._test_done,
            on_error=self._test_failed,
            name="CarenDMR-Verbindungstest",
        )

    def _test_done(self, message) -> None:
        self._set_busy(False)
        self._tested_ok = True
        self._say(str(message))
        self.save_button.setFocus()

    def _test_failed(self, error: Exception) -> None:
        self._set_busy(False)
        self._tested_ok = False
        text = f"Verbindungstest fehlgeschlagen: {error}"
        self._say(text)
        QMessageBox.warning(
            self,
            "CarenDMR",
            text + "\n\nBitte DMR-ID, Hotspot-Passwort und Server prüfen. Das Passwort ist "
            "das Hotspot-Sicherheitspasswort aus BrandMeister SelfCare.",
        )
        self.password_edit.setFocus()

    def _save(self) -> None:
        if self._background.busy:
            return
        try:
            values = self._values()
        except ValueError as error:
            QMessageBox.warning(self, "CarenDMR", str(error))
            return
        if not self._tested_ok and not self._connection_active():
            answer = QMessageBox.question(
                self,
                "CarenDMR",
                "Die Verbindung wurde noch nicht erfolgreich getestet. Trotzdem speichern?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                self.test_button.setFocus()
                return
        try:
            self._settings.save_station(**values)
        except ValueError as error:
            QMessageBox.warning(self, "CarenDMR", str(error))
            return
        QMessageBox.information(self, "CarenDMR", "Die Stationsdaten wurden gespeichert.")
        self.accept()

    def reject(self) -> None:
        if self._background.busy:
            self._say("Der Verbindungstest läuft noch. Bitte kurz warten.")
            return
        super().reject()


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
        # Der Hinweis „Einrichtung erscheint beim nächsten Start …“ gehört
        # nicht in den Einrichtungsdialog selbst.
        self.status_label.setText(report.message.replace(" " + SETUP_HINT, ""))
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


class AudioSetupDialog(QDialog):
    """Mikrofon und Lautsprecher wählen, mit kurzem Probeton."""

    def __init__(self, audio, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._audio = audio
        self.setWindowTitle("CarenDMR – Audio einrichten")
        self.setAccessibleName("Audio einrichten")
        self.setModal(True)

        layout = QVBoxLayout(self)
        intro = QLabel(
            "Bitte Mikrofon und Lautsprecher für CarenDMR wählen. Mit "
            "„Probeton“ ist auf dem gewählten Lautsprecher ein kurzer Ton zu hören."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form = QFormLayout()
        self.input_combo = QComboBox()
        _labeled(form, "&Mikrofon:", self.input_combo, "Mikrofon")
        self.output_combo = QComboBox()
        _labeled(form, "&Lautsprecher:", self.output_combo, "Lautsprecher")
        layout.addLayout(form)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setAccessibleName("Status der Audioeinrichtung")
        layout.addWidget(self.status_label)

        buttons = QDialogButtonBox()
        self.tone_button = buttons.addButton("&Probeton", QDialogButtonBox.ButtonRole.ActionRole)
        self.save_button = buttons.addButton("&Speichern", QDialogButtonBox.ButtonRole.AcceptRole)
        later = buttons.addButton("Später", QDialogButtonBox.ButtonRole.RejectRole)
        self.tone_button.clicked.connect(self._tone)
        self.save_button.clicked.connect(self._save)
        later.clicked.connect(self.reject)
        layout.addWidget(buttons)

        self._load()
        self.input_combo.setFocus()

    def _say(self, text: str) -> None:
        self.status_label.setText(text)
        announce(self.status_label, text)

    def _load(self) -> None:
        try:
            inputs, outputs = self._audio.scan()
        except Exception as error:
            self.status_label.setText(f"Audiogeräte konnten nicht eingelesen werden: {error}")
            self.save_button.setEnabled(False)
            self.tone_button.setEnabled(False)
            return
        for choice in inputs:
            self.input_combo.addItem(choice.label, choice.key)
        for choice in outputs:
            self.output_combo.addItem(choice.label, choice.key)
        current_input, current_output = self._audio.current_keys()
        for combo, key in ((self.input_combo, current_input), (self.output_combo, current_output)):
            index = combo.findData(key) if key else -1
            if index >= 0:
                combo.setCurrentIndex(index)
        self.status_label.setText(
            f"{len(inputs)} Mikrofon(e) und {len(outputs)} Lautsprecher gefunden."
        )

    def _tone(self) -> None:
        key = self.output_combo.currentData()
        if not key:
            return
        try:
            self._audio.play_test_tone(key)
        except Exception as error:
            QMessageBox.warning(self, "CarenDMR", f"Der Probeton konnte nicht abgespielt werden: {error}")
            return
        self._say("Probeton abgespielt.")

    def _save(self) -> None:
        input_key = self.input_combo.currentData()
        output_key = self.output_combo.currentData()
        if not input_key or not output_key:
            QMessageBox.warning(self, "CarenDMR", "Bitte Mikrofon und Lautsprecher wählen.")
            return
        try:
            self._audio.save(input_key, output_key)
        except Exception as error:
            QMessageBox.warning(self, "CarenDMR", str(error))
            return
        QMessageBox.information(self, "CarenDMR", "Die Audiogeräte wurden gespeichert.")
        self.accept()


class ContactsDialog(QDialog):
    """Lädt die RadioID-Kontaktdaten (Namen und Rufzeichen zu DMR-IDs)."""

    def __init__(self, contacts, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._contacts = contacts
        self._background = _Background(self)
        self.setWindowTitle("CarenDMR – Kontaktdaten laden")
        self.setAccessibleName("Kontaktdaten laden")
        self.setModal(True)

        layout = QVBoxLayout(self)
        info = QLabel(
            "Damit beim Empfang Rufzeichen und Namen angesagt werden, lädt CarenDMR "
            "einmal die Kontaktdaten von RadioID.net. Das dauert je nach Verbindung "
            "eine bis mehrere Minuten."
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        self.status_label = QLabel("Noch nicht geladen.")
        self.status_label.setWordWrap(True)
        self.status_label.setAccessibleName("Status der Kontaktdaten")
        layout.addWidget(self.status_label)

        buttons = QDialogButtonBox()
        self.load_button = buttons.addButton("&Jetzt laden", QDialogButtonBox.ButtonRole.AcceptRole)
        self.later_button = buttons.addButton("Später", QDialogButtonBox.ButtonRole.RejectRole)
        self.load_button.clicked.connect(self._load)
        self.later_button.clicked.connect(self.reject)
        layout.addWidget(buttons)
        self.load_button.setFocus()

    def _say(self, text: str) -> None:
        self.status_label.setText(text)
        announce(self.status_label, text)

    def _load(self) -> None:
        if self._background.busy:
            return
        self.load_button.setEnabled(False)
        self._say("Kontaktdaten werden geladen. Bitte warten.")
        self._background.start(
            lambda _progress: self._contacts.update(),
            on_done=self._done,
            on_error=self._failed,
            name="CarenDMR-Kontakte",
        )

    def _done(self, result) -> None:
        count, updated = result
        text = f"Kontaktdaten geladen: {count} Einträge, Stand {updated}."
        self._say(text)
        QMessageBox.information(self, "CarenDMR", text)
        self.accept()

    def _failed(self, error: Exception) -> None:
        self.load_button.setEnabled(True)
        text = f"Kontaktdaten konnten nicht geladen werden: {error}"
        self._say(text)
        QMessageBox.warning(self, "CarenDMR", text + "\n\nSpäter in den Einstellungen erneut versuchen.")

    def reject(self) -> None:
        if self._background.busy:
            self._say("Die Kontaktdaten werden noch geladen. Bitte kurz warten.")
            return
        super().reject()


def run_first_run_setup(services, parent: QWidget | None = None) -> None:
    """Zeigt fehlende Einrichtungsschritte vor dem ersten Fenster.

    Reihenfolge: Station, Sprach-Codec, Audio, Kontaktdaten. ``services`` ist
    ein ``FirstRunServices`` aus ``carendmr.bootstrap``. Jeder Schritt lässt
    sich mit „Später“ überspringen; CarenDMR startet dann trotzdem.
    """
    if services.station_settings.needs_setup():
        StationSetupDialog(services.station_settings, parent).exec()
    if services.codec_setup.status().state is CodecState.FILES_MISSING:
        CodecSetupDialog(services.codec_setup, parent).exec()
    if services.audio_setup.needs_setup():
        AudioSetupDialog(services.audio_setup, parent).exec()
    if services.contacts.needs_update():
        ContactsDialog(services.contacts, parent).exec()
