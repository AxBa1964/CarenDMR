"""Qt-Ansicht für den passiven DMR-Audio-Benchmark."""
from __future__ import annotations
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QFormLayout, QFrame, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QAbstractItemView, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)


class AudioBenchmarkWidget(QWidget):
    REFERENCE_TEXT = (
        "CQ CQ CQ, hier ist Delta Oscar Eins Delta Papa Lima. Dies ist der CarenDMR "
        "Audio-Referenztest. Eins, zwei, drei, vier, fünf, sechs, sieben, acht, neun, zehn. "
        "Anton, Berta, Cäsar, Dora, Emil, Friedrich, Gustav. Vielen Dank für diesen Test."
    )

    def __init__(self, service, *, current_target, reconnect_request, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.current_target = current_target
        self.reconnect_request = reconnect_request
        self.setAccessibleName("DMR-Audio-Benchmark")

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(10)

        heading = QLabel("DMR-AUDIO-BENCHMARK")
        heading.setObjectName("sectionTitle")
        root.addWidget(heading)
        info = QLabel(
            "Sammelt passiv technisch saubere Empfangsdurchgänge ab fünf Sekunden. "
            "Die Funk- und Audiowiedergabe wird nicht verändert."
        )
        info.setWordWrap(True)
        info.setObjectName("secondaryText")
        root.addWidget(info)

        controls = QHBoxLayout()
        self.start_button = QPushButton("Start")
        self.pause_button = QPushButton("Pause")
        self.resume_button = QPushButton("Fortsetzen")
        self.stop_button = QPushButton("Beenden")
        self.reset_button = QPushButton("Neue Messreihe")
        for button in (self.start_button, self.pause_button, self.resume_button, self.stop_button, self.reset_button):
            controls.addWidget(button)
        controls.addStretch(1)
        root.addLayout(controls)

        stats_frame = QFrame(self)
        stats_frame.setObjectName("card")
        stats = QFormLayout(stats_frame)
        self.status_label = QLabel("Bereit")
        self.reference_name_label = QLabel("–")
        self.target_label = QLabel("–")
        self.runtime_label = QLabel("00:00:00")
        self.current_station_label = QLabel("–")
        self.current_duration_label = QLabel("00:00")
        self.station_label = QLabel("0")
        self.case_label = QLabel("0 gültig / 0 verworfen")
        self.speech_time_label = QLabel("00:00:00")
        self.maturity_label = QLabel("0 % · 0 von 20 Stationen")
        self.queue_label = QLabel("0")
        self.reconnect_label = QLabel("0 von 5")
        stats.addRow("Status", self.status_label)
        stats.addRow("Referenz", self.reference_name_label)
        stats.addRow("Messziel", self.target_label)
        stats.addRow("Aktive Laufzeit", self.runtime_label)
        stats.addRow("Aktuelle Station", self.current_station_label)
        stats.addRow("Aktuelle Sprechdauer", self.current_duration_label)
        stats.addRow("Unterschiedliche Rufzeichen", self.station_label)
        stats.addRow("Testfälle", self.case_label)
        stats.addRow("Gültige Sprachzeit", self.speech_time_label)
        stats.addRow("Referenzreife", self.maturity_label)
        stats.addRow("Analysewarteschlange", self.queue_label)
        stats.addRow("Wiederverbindung", self.reconnect_label)
        root.addWidget(stats_frame)

        ref_heading = QLabel("Aktuelle Referenz")
        ref_heading.setObjectName("sectionTitle")
        root.addWidget(ref_heading)
        self.reference_table = QTableWidget(0, 2, self)
        self.reference_table.setHorizontalHeaderLabels(["Kennzahl", "Median / Referenzbereich"])
        self.reference_table.horizontalHeader().setStretchLastSection(True)
        self.reference_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.reference_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        root.addWidget(self.reference_table, 1)

        self.start_button.clicked.connect(self._start)
        self.pause_button.clicked.connect(self.service.pause)
        self.resume_button.clicked.connect(self.service.resume)
        self.stop_button.clicked.connect(self.service.stop)
        self.reset_button.clicked.connect(self._reset)

        self.service.subscribe(lambda _snapshot: None)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)
        self.refresh()

    def _start(self) -> None:
        tg, ts = self.current_target()
        self.service.start(tg, ts)
        self.refresh()

    def _reset(self) -> None:
        answer = QMessageBox.question(
            self, "Neue Benchmark-Messreihe",
            "Die bisherige Messreihe wird verworfen und eine neue für die aktuelle Talkgroup begonnen. Fortfahren?"
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        tg, ts = self.current_target()
        self.service.reset(tg, ts)
        self.refresh()

    @staticmethod
    def _duration(seconds: float) -> str:
        total = max(0, int(seconds))
        return f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}"

    def refresh(self) -> None:
        snap = self.service.snapshot()
        labels = {"idle": "Bereit", "running": "Läuft", "paused": "Pausiert", "stopped": "Beendet", "failed": "Abgebrochen"}
        self.status_label.setText(labels.get(snap["status"], snap["status"]))
        self.reference_name_label.setText(str(snap.get("reference_name", "–")).replace("_", " "))
        self.target_label.setText(f"TG {snap['talkgroup']} · TS{snap['timeslot']}")
        self.runtime_label.setText(self._duration(snap["active_seconds"]))
        active = snap.get("active_stream") or {}
        if active:
            label = active.get("callsign") or f"DMR-ID {active.get('dmr_id', '')}"
            self.current_station_label.setText(str(label))
            seconds = max(0, int(active.get("duration_seconds", 0)))
            self.current_duration_label.setText(f"{seconds // 60:02d}:{seconds % 60:02d}")
        else:
            self.current_station_label.setText("–")
            self.current_duration_label.setText("00:00")
        self.station_label.setText(str(snap["unique_callsigns"]))
        self.case_label.setText(f"{snap['accepted']} gültig / {snap['rejected']} verworfen")
        self.speech_time_label.setText(self._duration(snap.get("accepted_speech_seconds", 0)))
        self.maturity_label.setText(f"{snap.get('reference_maturity', 0)} % · {snap['unique_callsigns']} von {snap.get('reference_target', 20)} Stationen")
        self.queue_label.setText(str(snap.get("analysis_queue", 0)))
        self.reconnect_label.setText(f"{snap['reconnect_attempts']} von 5")
        running = snap["status"] == "running"
        paused = snap["status"] == "paused"
        self.start_button.setEnabled(not running)
        self.pause_button.setEnabled(running)
        self.resume_button.setEnabled(paused)
        self.stop_button.setEnabled(running or paused)
        self._show_reference(snap.get("reference") or {})

    def _show_reference(self, ref: dict) -> None:
        rows = [
            ("Stationen in Referenz", ref.get("stations")),
            ("Gültige QSOs", ref.get("qsos")),
            ("Referenz-Sprachzeit", self._duration(ref.get("speech_seconds", 0)) if ref.get("speech_seconds") is not None else None),
            ("Qualitätsindex", self._range(ref, "quality_score", "/100")),
            ("Peak", self._range(ref, "peak_dbfs", "dBFS")),
            ("RMS gesamt", self._range(ref, "rms_dbfs", "dBFS")),
            ("RMS Sprache", self._range(ref, "active_rms_dbfs", "dBFS")),
            ("Crest-Faktor", self._range(ref, "crest_factor_db", "dB")),
            ("Spektralschwerpunkt", self._range(ref, "spectral_centroid_hz", "Hz")),
            ("Bass 120–300 Hz", self._range(ref, "bass_percent", "%")),
            ("Sprachmitten 300–1500 Hz", self._range(ref, "mid_percent", "%")),
            ("Präsenz 1500–2500 Hz", self._range(ref, "presence_percent", "%")),
            ("Höhen 2500–3400 Hz", self._range(ref, "treble_percent", "%")),
            ("Sprechpausen", self._range(ref, "silence_percent", "%")),
            ("Pegelstabilität", self._range(ref, "level_stability_db", "dB")),
        ]
        rows = [(name, value) for name, value in rows if value not in (None, "")]
        self.reference_table.setRowCount(len(rows))
        for row, (name, value) in enumerate(rows):
            self.reference_table.setItem(row, 0, QTableWidgetItem(str(name)))
            self.reference_table.setItem(row, 1, QTableWidgetItem(str(value)))

    @staticmethod
    def _range(ref: dict, key: str, suffix: str) -> str:
        if key not in ref:
            return ""
        median = ref[key]
        if key + "_q25" in ref and key + "_q75" in ref:
            return f"{median:g} {suffix} · {ref[key + '_q25']:g} bis {ref[key + '_q75']:g} {suffix}"
        return f"{median:g} {suffix}"
