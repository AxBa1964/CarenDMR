"""Barrierefreies Live-Audiolabor mit A/B-Wiedergabe und Vierer-Verlauf."""
from __future__ import annotations

import queue
from threading import Thread

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QAbstractItemView, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)


class AudioLabWidget(QWidget):
    def __init__(self, service, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self._events: queue.SimpleQueue[tuple[str, object]] = queue.SimpleQueue()
        self._current = None
        self._build()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(100)
        self.refresh_history()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        intro = QLabel(
            "Lokaler DMR-Audiotest ohne BrandMeister. Aufnahme und TX-Aufbereitung "
            "verwenden denselben CarenDMR-Livepfad wie PTT; AMBE-Encoder, AMBE-Decoder "
            "und RX-Ausgabe sind ebenfalls die produktiven Komponenten."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        controls = QHBoxLayout()
        self.start_button = QPushButton("Aufnahme starten")
        self.stop_button = QPushButton("Aufnahme beenden und anhören")
        self.stop_button.setEnabled(False)
        self.decoder_a_button = QPushButton("A hören – alter CarenDMR-Pfad")
        self.decoder_b_button = QPushButton("B hören – produktiver Referenzpfad")
        self.original_button = QPushButton("Original anhören")
        self.decoder_a_button.setEnabled(False)
        self.decoder_b_button.setEnabled(False)
        self.original_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_recording)
        self.stop_button.clicked.connect(self.finish_recording)
        self.decoder_a_button.clicked.connect(self.play_decoder_a)
        self.decoder_b_button.clicked.connect(self.play_decoder_b)
        self.original_button.clicked.connect(self.play_original)
        for button in (
            self.start_button, self.stop_button, self.decoder_a_button,
            self.decoder_b_button, self.original_button
        ):
            controls.addWidget(button)
        layout.addLayout(controls)

        self.status = QLabel("Bereit.")
        self.status.setAccessibleName("Status Audiolabor")
        layout.addWidget(self.status)

        settings_box = QGroupBox("Aktueller Durchgang")
        settings_layout = QGridLayout(settings_box)
        self.settings_label = QLabel("Noch kein Durchgang.")
        self.settings_label.setWordWrap(True)
        self.quality_label = QLabel("")
        self.quality_label.setWordWrap(True)
        settings_layout.addWidget(self.settings_label, 0, 0)
        settings_layout.addWidget(self.quality_label, 1, 0)
        layout.addWidget(settings_box)

        history_box = QGroupBox("Aktuell und letzte drei Durchgänge")
        history_layout = QVBoxLayout(history_box)
        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels([
            "Zeit", "Mikrofon", "Gain", "Profil", "TX dBFS", "Codec dBFS",
            "RX dBFS", "Codec Δ dB", "Ähnlichkeit %", "Clipping"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        self.table.setAccessibleName("Vergleich der letzten vier Audio-Durchgänge")
        history_layout.addWidget(self.table)
        layout.addWidget(history_box)

    def start_recording(self) -> None:
        try:
            self.service.start_recording(max_duration_seconds=30.0)
        except Exception as error:
            QMessageBox.critical(self, "CarenDMR – Audiolabor", str(error))
            return
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.decoder_a_button.setEnabled(False)
        self.decoder_b_button.setEnabled(False)
        self.original_button.setEnabled(False)
        self.status.setText("Aufnahme läuft. Sprechen Sie jetzt; anschließend Aufnahme beenden.")

    def finish_recording(self) -> None:
        self.stop_button.setEnabled(False)
        self.status.setText(
            "Verarbeite lokal: ein MD380-Encode, danach Decoder A und Decoder B …"
        )
        def worker():
            try:
                run = self.service.finish_recording_and_play()
                self._events.put(("finished", run))
            except Exception as error:
                self._events.put(("error", error))
        Thread(target=worker, name="CarenDMR-LocalAudioLab", daemon=True).start()

    def _poll(self) -> None:
        while True:
            try:
                kind, value = self._events.get_nowait()
            except queue.Empty:
                return
            if kind == "finished":
                self._current = value
                self.start_button.setEnabled(True)
                self.decoder_a_button.setEnabled(True)
                self.decoder_b_button.setEnabled(True)
                self.original_button.setEnabled(True)
                self.status.setText(
                    "Fertig. A und B können jetzt direkt gegeneinander gehört werden."
                )
                self._show_run(value)
                self.refresh_history()
            elif kind == "replayed":
                self.decoder_a_button.setEnabled(True)
                self.decoder_b_button.setEnabled(True)
                self.original_button.setEnabled(True)
                self.status.setText("Wiedergabe beendet.")
            elif kind == "error":
                self.start_button.setEnabled(True)
                self.stop_button.setEnabled(False)
                self.decoder_a_button.setEnabled(True)
                self.decoder_b_button.setEnabled(True)
                self.original_button.setEnabled(True)
                self.status.setText("Fehler im Audiolabor.")
                QMessageBox.critical(self, "CarenDMR – Audiolabor", str(value))

    @staticmethod
    def _value(run, group, point, key, default=0.0):
        try:
            return run.metrics[group][point][key]
        except Exception:
            return default

    def _show_run(self, run) -> None:
        s = run.settings
        self.settings_label.setText(
            f"Mikrofon: {s.get('microphone','')} | Gain: {s.get('microphone_gain_percent','')} % | "
            f"Profil: {s.get('tx_profile','')} | Sprachaufbereitung: "
            f"{'an' if s.get('tx_speech_processing_enabled') else 'aus'} | "
            f"RX: {s.get('rx_volume_percent','')} % | AGC: "
            f"{'an' if s.get('rx_agc_enabled') else 'aus'}"
        )
        levels = run.metrics.get("levels", {})
        q = run.metrics.get("quality", {})
        before_a = levels.get("before_ambe_8k", {})
        before_b = levels.get("droidstar_reference_before_ambe_8k", {})
        a = levels.get("decoder_a_carendmr_8k", {})
        b = levels.get("decoder_b_droidstar_reference_8k", levels.get("after_codec_8k", {}))
        rx_a = levels.get("rx_a_carendmr_native", {})
        rx_b = levels.get("rx_b_droidstar_reference_native", levels.get("rx_before_soundcard_native", {}))
        qa = q.get("path_a_carendmr", {})
        qb = q.get("path_b_droidstar_reference", {})
        self.quality_label.setText(
            f"A vor AMBE {before_a.get('rms_dbfs', -120):.2f} dBFS | "
            f"B vor AMBE {before_b.get('rms_dbfs', -120):.2f} dBFS | "
            f"A nach MD380 {a.get('rms_dbfs', -120):.2f} dBFS | "
            f"B nach MD380 {b.get('rms_dbfs', -120):.2f} dBFS | "
            f"A Codec Δ {qa.get('codec_rms_change_db', 0):+.2f} dB | "
            f"B Codec Δ {qb.get('codec_rms_change_db', 0):+.2f} dB | "
            f"A Präsenz {qa.get('presence_band_percent', 0):.1f}% | "
            f"B Präsenz {qb.get('presence_band_percent', 0):.1f}% | "
            f"Clipping A {a.get('clipped_samples', 0)} / B {b.get('clipped_samples', 0)}"
        )

    def refresh_history(self) -> None:
        runs = self.service.load_history(limit=4)
        self.table.setRowCount(len(runs))
        for row, run in enumerate(reversed(runs)):
            s = run.settings
            levels = run.metrics.get("levels", {})
            q = run.metrics.get("quality", {})
            before = levels.get("before_ambe_8k", {})
            codec = levels.get("after_codec_8k", {})
            rx = levels.get("rx_before_soundcard_native", levels.get("rx_before_soundcard_8k", {}))
            created = str(run.created_at)[11:19] if len(str(run.created_at)) >= 19 else str(run.created_at)
            values = [
                created,
                str(s.get("microphone", "")),
                f"{s.get('microphone_gain_percent', '')} %",
                str(s.get("tx_profile", "")),
                f"{before.get('rms_dbfs', -120):.2f}",
                f"{codec.get('rms_dbfs', -120):.2f}",
                f"{rx.get('rms_dbfs', -120):.2f}",
                f"{q.get('codec_rms_change_db', 0):+.2f}",
                f"{q.get('similarity_percent', 0):.1f}",
                str(before.get("clipped_samples", 0)),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(0x0100, run.run_id)  # Qt.UserRole without extra import.
                self.table.setItem(row, column, item)
        self.table.resizeColumnsToContents()
        if self.table.rowCount():
            self.table.selectRow(0)

    def _selected_run(self):
        row = self.table.currentRow()
        if row < 0:
            return self._current
        item = self.table.item(row, 0)
        run_id = item.data(0x0100) if item is not None else None
        for run in self.service.load_history(limit=30):
            if run.run_id == run_id:
                return run
        return self._current

    def _selection_changed(self) -> None:
        run = self._selected_run()
        if run is not None:
            self._current = run
            self._show_run(run)
            self.decoder_a_button.setEnabled(True)
            self.decoder_b_button.setEnabled(True)
            self.original_button.setEnabled(True)
            self.original_button.setEnabled(True)

    def _play_async(self, fn, text: str) -> None:
        self.status.setText(text)
        self.decoder_a_button.setEnabled(False)
        self.decoder_b_button.setEnabled(False)
        self.original_button.setEnabled(False)
        def worker():
            try:
                fn()
                self._events.put(("replayed", None))
            except Exception as error:
                self._events.put(("error", error))
        Thread(target=worker, name="CarenDMR-AudioLab-Wiedergabe", daemon=True).start()

    def play_decoder_a(self) -> None:
        run = self._selected_run()
        if run is None:
            return
        self._play_async(
            lambda: self.service.play_decoder_a(run),
            "Spiele A: heutiger CarenDMR-TX-Pfad → MD380 …",
        )

    def play_decoder_b(self) -> None:
        run = self._selected_run()
        if run is None:
            return
        self._play_async(
            lambda: self.service.play_decoder_b(run),
            "Spiele B: neutraler DroidStar-Referenzpfad → MD380 …",
        )

    def play_original(self) -> None:
        run = self._selected_run()
        if run is None:
            return
        self._play_async(lambda: self.service.play_original(run), "Spiele Mikrofon-Original …")
