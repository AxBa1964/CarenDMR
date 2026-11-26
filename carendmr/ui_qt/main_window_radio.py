"""Funkbetrieb des Hauptfensters: Verbinden, Trennen, PTT/TX und Bedienfreigaben.

Der eigentliche Funkablauf läuft über den OperatingController; hier liegen
nur Anzeige, Signaltöne, Screenreader-Vorlauf und TX-Zeitanzeige.

Teil von ``MainWindow`` (siehe main_window.py). Die Methoden wurden ab
0.2.1.87 unverändert aus dem Hauptfenster hierher verschoben.
"""
from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMessageBox
from threading import Thread
from carendmr.application import RadioState


class MainWindowRadioMixin:
    """Mixin für ``MainWindow``; setzt dessen Attribute voraus."""

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
            self._apply_channel_rules()
            tg, ts, call_type = self._target()
            self._save_preferences()
        except Exception as error:
            QMessageBox.warning(self, "CarenDMR", str(error))
            return
        self._startup_announcement_timer.stop()
        try:
            self.controller.connect_async(
                tg, ts, call_type,
                on_done=lambda started: self._updates.put(("connect_result", started)),
                on_error=lambda error: self._updates.put(("connect_error", error)),
            )
        except (RuntimeError, ValueError) as error:
            QMessageBox.warning(self, "CarenDMR", str(error))
            return
        self._connected_announcement_pending = True
        self.connection_indicator.set_state("busy")
        self.statusBar().showMessage("Verbindung wird hergestellt …")
        self._set_controls_for_state(self.radio_state.state)

    def _apply_channel_rules(self) -> None:
        """9990 (Papagei) braucht einen Privatruf; sonst bleibt alles unverändert."""
        from carendmr.application.channel_rules import required_call_type

        text = self.current_tg_label.text().strip()
        if not text.isdigit():
            return
        call_type, notice = required_call_type(int(text), self._selected_call_type)
        if notice is None:
            return
        self._select_call_type(call_type)
        self.accessibility.announcer.announce(
            self.connection_label, notice, channel="parrot-private", force=True
        )
        self.statusBar().showMessage(notice, 5000)

    def _disconnect(self) -> None:
        self._stop_qso_recording("Mitschnitt wegen Trennen beendet")
        if self._tx_active:
            self._stop_tx()
        # Der Controller beendet eine noch laufende Sendung und wartet bis zu
        # 8 Sekunden auf das Ende des Empfangs.
        self.controller.disconnect_async(
            wait_timeout=8.0,
            on_done=lambda _finished: self._updates.put(("disconnect_result", True)),
            on_error=lambda error: self._updates.put(("disconnect_error", error)),
        )
        self.statusBar().showMessage("Empfang und Verbindung werden beendet …")
        self._set_controls_for_state(self.radio_state.state)

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
        try:
            # Der Controller schaltet auf TRANSMITTING und sendet im Hintergrund.
            self._tx_stop_event = self.controller.start_ptt(
                level_callback=lambda level: self._updates.put(("mic_level", level)),
                optimize=True,
                tx_complete_callback=lambda: self._updates.put(("tx_wire_complete", None)),
                on_done=lambda result: self._updates.put(("tx_result", result)),
                on_error=lambda error: self._updates.put(("tx_error", error)),
            )
        except RuntimeError as error:
            self._cancel_pending_tx()
            self.statusBar().showMessage(str(error))
            return
        self._tx_active = True
        self._tx_stopping = False
        self._tx_elapsed_seconds = 0
        self._tx_warning_played = False
        self._tx_elapsed_timer.start()
        self.ptt_button.setText("TX")
        self.ptt_button.setProperty("visualState", "tx")
        self.ptt_button.style().unpolish(self.ptt_button)
        self.ptt_button.style().polish(self.ptt_button)
        self.tx_status.setText("TX")
        self.statusBar().showMessage("TX")
        self._set_controls_for_state(self.radio_state.state)

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
        self.controller.stop_ptt()
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
        # Den Bedienzustand nach TX hat der OperatingController bereits gesetzt.
        state = self.radio_state.state
        self.ptt_button.setText("TX")
        self.ptt_button.setProperty("visualState", "ready" if state is RadioState.CONNECTED else "idle")
        self.ptt_button.style().unpolish(self.ptt_button)
        self.ptt_button.style().polish(self.ptt_button)
        self.tx_status.setText("RX")
        self.statusBar().showMessage(message)
        self._set_controls_for_state(state)

    def _verify_encoder(self) -> None:
        def worker() -> None:
            try:
                diagnostics = self.encoder_service.verify_configured()
                self._updates.put(("encoder_ready", diagnostics))
            except Exception as error:
                self._updates.put(("encoder_error", error))
        Thread(target=worker, name="CarenDMR-Qt-Encoder", daemon=True).start()
