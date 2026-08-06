"""Separate Qt-Oberfläche für den Modulationsvergleich von CarenDMR."""
from __future__ import annotations

from pathlib import Path

from carendmr.benchmark.modulation_test import ModulationTestTracker

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class AudioCoachWidget(QWidget):
    """Dünne Qt-Sicht auf Referenz und eigenen Modulationstest."""

    REFERENCE_TEXT = (
        "CQ CQ CQ, hier ist Delta Oscar Eins Delta Papa Lima. Dies ist der CarenDMR "
        "Audio-Referenztest. Eins, zwei, drei, vier, fünf, sechs, sieben, acht, neun, zehn. "
        "Anton, Berta, Cäsar, Dora, Emil, Friedrich, Gustav. Vielen Dank für diesen Test."
    )

    def __init__(self, service, *, start_modulation_test=None, cancel_modulation_test=None, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.start_modulation_test = start_modulation_test
        self.cancel_modulation_test = cancel_modulation_test
        self._comparison_waiting = False
        self._tracker = ModulationTestTracker(self.service.project_root / "logs" / "audio_lab")
        self._last_comparison: dict | None = None
        self.setAccessibleName("CarenDMR Audio Coach")

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(12)

        heading = QLabel("AUDIO COACH")
        heading.setObjectName("sectionTitle")
        root.addWidget(heading)

        intro = QLabel(
            "Vergleicht deine eigene, bereits durch AMBE verarbeitete Modulation mit der aktiven DMR-Referenz. "
            "Die vorgeschlagenen Werte werden nicht automatisch übernommen."
        )
        intro.setObjectName("secondaryText")
        intro.setWordWrap(True)
        root.addWidget(intro)

        reference_card = QFrame(self)
        reference_card.setObjectName("card")
        reference_layout = QHBoxLayout(reference_card)
        reference_layout.setContentsMargins(18, 14, 18, 14)
        self.reference_name_label = QLabel("Referenz: –")
        self.reference_name_label.setObjectName("fieldCaption")
        self.reference_summary_label = QLabel("Noch keine belastbare Referenz geladen.")
        self.reference_summary_label.setObjectName("secondaryText")
        reference_texts = QVBoxLayout()
        reference_texts.addWidget(self.reference_name_label)
        reference_texts.addWidget(self.reference_summary_label)
        reference_layout.addLayout(reference_texts, 1)
        root.addWidget(reference_card)

        workflow_card = QFrame(self)
        workflow_card.setObjectName("card")
        workflow_layout = QVBoxLayout(workflow_card)
        workflow_layout.setContentsMargins(18, 14, 18, 14)
        actions = QHBoxLayout()
        self.modulation_test_button = QPushButton("Eigene Modulation testen")
        self.modulation_test_button.setAccessibleName("Eigene Modulation gegen die aktive Referenz testen")
        actions.addWidget(self.modulation_test_button)
        actions.addStretch(1)
        workflow_layout.addLayout(actions)
        self.modulation_status = QLabel("Bereit. Noch kein Vergleich durchgeführt.")
        self.modulation_status.setWordWrap(True)
        workflow_layout.addWidget(self.modulation_status)
        self.reference_text_label = QLabel(self.REFERENCE_TEXT)
        self.reference_text_label.setWordWrap(True)
        self.reference_text_label.setObjectName("secondaryText")
        self.reference_text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByKeyboard | Qt.TextInteractionFlag.TextSelectableByMouse)
        workflow_layout.addWidget(self.reference_text_label)
        root.addWidget(workflow_card)

        result_heading = QLabel("Vergleich")
        result_heading.setObjectName("sectionTitle")
        root.addWidget(result_heading)
        self.comparison_table = QTableWidget(0, 5, self)
        self.comparison_table.setHorizontalHeaderLabels(["Kennzahl", "Referenz", "DO1DPL", "Abweichung", "Bewertung"])
        self.comparison_table.horizontalHeader().setStretchLastSection(True)
        self.comparison_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.comparison_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        root.addWidget(self.comparison_table, 1)

        self.modulation_test_button.clicked.connect(self._toggle_own_modulation_test)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)
        self.refresh()

    def _toggle_own_modulation_test(self) -> None:
        if self._comparison_waiting:
            self._cancel_own_modulation_test()
            return
        self._start_own_modulation_test()

    def _start_own_modulation_test(self) -> None:
        if self.start_modulation_test is None:
            QMessageBox.warning(self, "Modulationstest", "Der Modulationstest ist nicht verbunden.")
            return
        snap = self.service.snapshot()
        if int(snap.get("unique_callsigns", 0)) < 5:
            QMessageBox.warning(self, "Modulationstest", "Die aktive Referenz enthält noch zu wenige Stationen.")
            return
        try:
            self.start_modulation_test()
        except Exception as exc:
            QMessageBox.warning(self, "Modulationstest", str(exc))
            return
        self._tracker.arm()
        self._comparison_waiting = True
        self.modulation_test_button.setText("Abbrechen")
        self.modulation_test_button.setEnabled(True)
        self.modulation_status.setText(
            "Parrot vorbereitet. Auf der Betriebsseite verbinden, TX drücken, den Referenztext sprechen "
            "und die vollständige Antwort abwarten."
        )

    def _poll_modulation_test(self) -> None:
        if not self._comparison_waiting:
            return
        snapshot = self._tracker.poll()
        self.modulation_status.setText(snapshot.message)
        if snapshot.failed:
            self._finish_failed(snapshot.message)
            return
        if not snapshot.ready_for_comparison or snapshot.session_dir is None:
            return
        try:
            result = self.service.compare_audio_test(snapshot.session_dir)
        except RuntimeError as exc:
            self.modulation_status.setText(f"Test gespeichert. Vergleich wartet: {exc}")
            return
        except Exception as exc:
            self._finish_failed(f"Vergleich fehlgeschlagen: {exc}")
            return
        self._last_comparison = result
        self._finish_test(True, "Modulationstest und Vergleich abgeschlossen.")
        self._show_comparison(result)

    def _cancel_own_modulation_test(self) -> None:
        message = "Modulationstest abgebrochen."
        try:
            self._tracker.abort(message)
        except Exception as exc:
            message = f"{message} Statusdatei meldete: {exc}"
        self._finish_test(False, message, invoke_cancel=True)

    def _finish_test(self, success: bool, message: str, *, invoke_cancel: bool = False) -> None:
        if invoke_cancel and self.cancel_modulation_test is not None:
            try:
                self.cancel_modulation_test()
            except Exception as exc:
                message = f"{message} Aufräumen meldete: {exc}"
        self._comparison_waiting = False
        self.modulation_test_button.setText("Eigene Modulation testen")
        self.modulation_test_button.setEnabled(True)
        self.modulation_status.setText(message)
        self._tracker.reset()

    def _finish_failed(self, message: str) -> None:
        self._finish_test(False, message, invoke_cancel=True)

    def _show_comparison(self, result: dict) -> None:
        rows = result.get("rows") or []
        recommendations = {item.get("parameter"): item for item in result.get("recommendations") or []}
        test_metadata = result.get("test_metadata") or {}
        self.comparison_table.setRowCount(len(rows))
        parameter_by_key = {
            "active_rms_dbfs": "Mic-Gain",
            "bass_percent": "Tiefen",
            "mid_percent": "Sprachmitten",
            "presence_percent": "Präsenz",
            "treble_percent": "Höhen",
            "crest_factor_db": "Dynamik",
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
            values = (
                str(item.get("label", "")),
                f"{float(item.get('reference', 0)):g} {unit}",
                f"{float(item.get('own', 0)):g} {unit}",
                f"{delta:+g} {unit}",
                assessment,
            )
            for column, value in enumerate(values):
                self.comparison_table.setItem(row, column, QTableWidgetItem(value))

        count = int(result.get("reference_stations", 0))
        tuner = test_metadata.get("tx_audio_tuner") or {}
        profile = str(tuner.get("profile", "Unbekannt"))
        gain = test_metadata.get("microphone_gain_percent")
        measured_with = f"Gemessen mit Profil {profile}" + (f", Mic-Gain {gain} %" if gain is not None else "")
        if result.get("recommendations"):
            summary = "; ".join(f"{r['parameter']} {int(r['change']):+d}" for r in result["recommendations"])
            self.modulation_status.setText(
                f"{measured_with}. Vergleich mit {result.get('reference_name', 'Referenz')} ({count} Stationen): "
                f"Empfohlene Änderungen: {summary}. Noch nichts wurde automatisch verändert."
            )
        else:
            self.modulation_status.setText(
                f"{measured_with}. Deine Modulation liegt nahe an "
                f"{result.get('reference_name', 'der Referenz')} ({count} Stationen)."
            )

    def refresh(self) -> None:
        snap = self.service.snapshot()
        reference_name = str(snap.get("reference_name", "–")).replace("_", " ")
        stations = int(snap.get("unique_callsigns", 0))
        qsos = int((snap.get("reference") or {}).get("qsos", snap.get("accepted", 0)) or 0)
        speech_seconds = float((snap.get("reference") or {}).get("speech_seconds", snap.get("accepted_speech_seconds", 0)) or 0)
        self.reference_name_label.setText(f"Referenz: {reference_name}")
        self.reference_summary_label.setText(
            f"{stations} Stationen · {qsos} gültige QSOs · {self._duration(speech_seconds)} Sprachzeit"
        )
        if not self._comparison_waiting:
            latest = getattr(self.service, "latest_comparison", None)
            if callable(latest):
                try:
                    result = latest()
                except Exception:
                    result = None
                if result and result != self._last_comparison:
                    self._last_comparison = result
                    self._show_comparison(result)
        self._poll_modulation_test()

    @staticmethod
    def _duration(seconds: float) -> str:
        total = max(0, int(seconds))
        return f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}"
