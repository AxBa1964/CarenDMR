"""Qt-Ansicht für den passiven DMR-Audio-Benchmark."""
from __future__ import annotations
from pathlib import Path
import json

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

    def __init__(self, service, *, current_target, reconnect_request, start_modulation_test=None, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.current_target = current_target
        self.reconnect_request = reconnect_request
        self.start_modulation_test = start_modulation_test
        self._comparison_waiting = False
        self._comparison_test_dir: Path | None = None
        self._comparison_rx_size: int | None = None
        self._comparison_stable_polls = 0
        self._known_audio_tests: set[str] = set()
        self._last_comparison = None
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

        compare_heading = QLabel("Eigene Modulation")
        compare_heading.setObjectName("sectionTitle")
        root.addWidget(compare_heading)
        compare_actions = QHBoxLayout()
        self.modulation_test_button = QPushButton("Eigene Modulation testen")
        self.modulation_test_button.setAccessibleName("Eigene Modulation gegen die aktive Referenz testen")
        self.modulation_status = QLabel("Noch kein Vergleich durchgeführt.")
        self.modulation_status.setWordWrap(True)
        compare_actions.addWidget(self.modulation_test_button)
        compare_actions.addWidget(self.modulation_status, 1)
        root.addLayout(compare_actions)
        self.comparison_table = QTableWidget(0, 5, self)
        self.comparison_table.setHorizontalHeaderLabels(["Kennzahl", "Referenz", "DO1DPL", "Abweichung", "Bewertung"])
        self.comparison_table.horizontalHeader().setStretchLastSection(True)
        self.comparison_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.comparison_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.comparison_table.setMaximumHeight(260)
        root.addWidget(self.comparison_table)

        self.start_button.clicked.connect(self._start)
        self.pause_button.clicked.connect(self.service.pause)
        self.resume_button.clicked.connect(self.service.resume)
        self.stop_button.clicked.connect(self.service.stop)
        self.reset_button.clicked.connect(self._reset)
        self.modulation_test_button.clicked.connect(self._start_own_modulation_test)

        self.service.subscribe(lambda _snapshot: None)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)
        self.refresh()

    def _audio_test_dirs(self) -> set[str]:
        root = self.service.project_root / "logs" / "audio_lab"
        if not root.exists():
            return set()
        return {str(path.resolve()) for path in root.glob("AudioTest_*") if path.is_dir()}

    def _start_own_modulation_test(self) -> None:
        if self.start_modulation_test is None:
            QMessageBox.warning(self, "Modulationstest", "Der Modulationstest ist in dieser Oberfläche nicht verbunden.")
            return
        snap = self.service.snapshot()
        if int(snap.get("unique_callsigns", 0)) < 5:
            QMessageBox.warning(self, "Modulationstest", "Die aktive Referenz enthält noch zu wenige Stationen. Bitte zunächst weiter sammeln.")
            return
        self._known_audio_tests = self._audio_test_dirs()
        try:
            self.start_modulation_test()
        except Exception as exc:
            QMessageBox.warning(self, "Modulationstest", str(exc))
            return
        self._known_audio_tests = self._audio_test_dirs()
        self._comparison_test_dir = None
        self._comparison_rx_size = None
        self._comparison_stable_polls = 0
        self._comparison_waiting = True
        self.modulation_test_button.setEnabled(False)
        self.modulation_status.setText("Parrot ist vorbereitet. Verbinden, TX drücken und den eingeblendeten Referenztext sprechen.")
        QMessageBox.information(
            self, "CarenDMR Audio-Referenztest",
            "Bitte nach dem TX-Beep gleichmäßig und in normaler Lautstärke sprechen:\n\n" + self.REFERENCE_TEXT +
            "\n\nAnschließend die vollständige Parrot-Antwort abwarten. Der Vergleich erscheint automatisch."
        )

    def _poll_modulation_test(self) -> None:
        if not self._comparison_waiting:
            return

        try:
            # Den neu entstandenen AudioTest-Ordner genau einmal übernehmen.
            if self._comparison_test_dir is None:
                current_dirs = self._audio_test_dirs()
                new_dirs = [
                    Path(value)
                    for value in current_dirs - self._known_audio_tests
                ]
                new_dirs = [path for path in new_dirs if path.is_dir()]

                if not new_dirs:
                    return

                self._comparison_test_dir = max(
                    new_dirs,
                    key=lambda path: path.stat().st_mtime,
                )

            test_dir = self._comparison_test_dir
            analysis_file = test_dir / "analysis.json"
            loopback_file = test_dir / "04_codec_loopback_8k.wav"

            if not analysis_file.is_file() or not loopback_file.is_file():
                return

            # Die vollständige Parrot-Rückantwort muss vorhanden sein.
            parrot_files = list(
                test_dir.glob("rx_*_parrot_nach_ambe_8k.wav")
            )
            if not parrot_files:
                return

            parrot_file = max(
                parrot_files,
                key=lambda path: path.stat().st_mtime,
            )

            # Prüfen, ob der Parrot laut Analyse wirklich vollständig empfangen wurde.
            with analysis_file.open("r", encoding="utf-8") as handle:
                analysis = json.load(handle)

            extra = analysis.get("extra", {})
            if extra.get("echo_received") is not True:
                return

            # RX-Datei muss über mehrere Timerdurchläufe unverändert sein.
            current_size = parrot_file.stat().st_size

            if current_size <= 44:
                return

            if current_size != self._comparison_rx_size:
                self._comparison_rx_size = current_size
                self._comparison_stable_polls = 0
                return

            self._comparison_stable_polls += 1

            # Erst nach zwei unveränderten Prüfungen auswerten.
            if self._comparison_stable_polls < 2:
                return

            result = self.service.compare_audio_test(test_dir)

        except RuntimeError:
            # Dateien oder Analyse sind noch nicht vollständig abgeschlossen.
            return

        except Exception as exc:
            self._comparison_waiting = False
            self._comparison_test_dir = None
            self._comparison_rx_size = None
            self._comparison_stable_polls = 0
            self.modulation_test_button.setEnabled(True)
            self.modulation_status.setText(
                f"Vergleich fehlgeschlagen: {exc}"
            )
            return

        self._comparison_waiting = False
        self._known_audio_tests.add(str(test_dir))
        self._comparison_test_dir = None
        self._comparison_rx_size = None
        self._comparison_stable_polls = 0

        self.modulation_test_button.setEnabled(True)
        self._last_comparison = result
        self.modulation_status.setText(
            "Modulationsvergleich abgeschlossen."
        )
        self._show_comparison(result)

    def _show_comparison(self, result: dict) -> None:
        rows = result.get("rows") or []
        recommendations = {item.get("parameter"): item for item in result.get("recommendations") or []}
        self.comparison_table.setRowCount(len(rows))
        parameter_by_key = {
            "active_rms_dbfs": "Mic-Gain", "bass_percent": "Tiefen",
            "mid_percent": "Sprachmitten", "presence_percent": "Präsenz",
            "treble_percent": "Höhen", "crest_factor_db": "Dynamik",
        }
        for row, item in enumerate(rows):
            unit = item.get("unit", "")
            delta = float(item.get("delta", 0.0))
            parameter = parameter_by_key.get(item.get("key"), "")
            recommendation = recommendations.get(parameter)
            assessment = "im Referenzbereich"
            if recommendation:
                change = int(recommendation.get("change", 0))
                assessment = f"{parameter} {change:+d}: {recommendation.get('reason', '')}"
            self.comparison_table.setItem(row, 0, QTableWidgetItem(str(item.get("label", ""))))
            self.comparison_table.setItem(row, 1, QTableWidgetItem(f"{float(item.get('reference',0)):g} {unit}"))
            self.comparison_table.setItem(row, 2, QTableWidgetItem(f"{float(item.get('own',0)):g} {unit}"))
            self.comparison_table.setItem(row, 3, QTableWidgetItem(f"{delta:+g} {unit}"))
            self.comparison_table.setItem(row, 4, QTableWidgetItem(assessment))
        count = int(result.get("reference_stations", 0))
        if result.get("recommendations"):
            summary = "; ".join(f"{r['parameter']} {int(r['change']):+d}" for r in result["recommendations"])
            self.modulation_status.setText(f"Vergleich mit {result.get('reference_name','Referenz')} ({count} Stationen): {summary}. Noch nichts wurde automatisch verändert.")
        else:
            self.modulation_status.setText(f"Deine Modulation liegt nahe an {result.get('reference_name','der Referenz')} ({count} Stationen).")

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
        self._poll_modulation_test()

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
