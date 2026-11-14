"""Audio-Bedienung, Audio-Tuner, Benchmark-Anbindung und QSO-Mitschnitt des Hauptfensters.

Teil von ``MainWindow`` (siehe main_window.py). Die Methoden wurden ab
0.2.1.87 unverändert aus dem Hauptfenster hierher verschoben.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
)
from carendmr.application.operating_preferences import OperatingPreferences
from carendmr.audio import TUNER_PRESETS, TxAudioTunerSettings
from carendmr.domain import DmrChannel


class MainWindowAudioMixin:
    """Mixin für ``MainWindow``; setzt dessen Attribute voraus."""

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
