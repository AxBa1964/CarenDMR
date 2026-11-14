"""QSO-Historie, QRZ.com (Abfrage und Logbook) und ADIF-UDP des Hauptfensters.

Teil von ``MainWindow`` (siehe main_window.py). Die Methoden wurden ab
0.2.1.87 unverändert aus dem Hauptfenster hierher verschoben.
"""
from __future__ import annotations

from PySide6.QtWidgets import QMessageBox
from datetime import datetime, timezone
from threading import Thread
from carendmr.adif_udp import AdifUdpError
from carendmr.qrz import QrzLogbookError, QrzNotFound, QrzServiceError
from carendmr.ui_qt.qrz_window import QrzStationWindow


class MainWindowLogbookMixin:
    """Mixin für ``MainWindow``; setzt dessen Attribute voraus."""

    def _sync_qso_history(self) -> None:
        try:
            message = self.receive_service.history.sync_now()
            if hasattr(self, "history_widget"):
                self.history_widget.refresh()
            self._refresh_recent_stations(force=True)
            self._show_status(message)
        except Exception as exc:
            QMessageBox.critical(self, "QSO-Synchronisation", str(exc))
            self._show_status(f"QSO-Synchronisation fehlgeschlagen: {exc}")

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
            self.qso_status_label.setText("Keine Station aktiv")
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

    def _send_history_qso_adif_udp(self, summary) -> None:
        if not self.adif_udp_service.configured:
            QMessageBox.information(
                self, "ADIF-UDP",
                "ADIF-UDP ist noch nicht aktiviert. Bitte zuerst unter Einstellungen → Datenbanken Adresse und Port festlegen."
            )
            return
        if not summary.worked or not summary.worked_at or not summary.callsign:
            self.statusBar().showMessage("ADIF-UDP: Nur bestätigte QSOs mit Rufzeichen können gesendet werden.")
            return
        try:
            qso_at = datetime.fromisoformat(summary.worked_at)
            station_callsign = self.station_settings.station_callsign()
            cfg = self.adif_udp_service.config
        except Exception as error:
            QMessageBox.warning(self, "ADIF-UDP", f"QSO-Daten konnten nicht vorbereitet werden: {error}")
            return
        callsign = summary.callsign.strip().upper()
        answer = QMessageBox.question(
            self, "QSO per ADIF-UDP senden",
            f"{callsign} · {qso_at.astimezone(timezone.utc).strftime('%d.%m.%Y %H:%M UTC')} · 70cm · DMR\n"
            f"BrandMeister TG {summary.last_talkgroup} · TS{summary.last_timeslot}\n"
            f"Empfänger: {cfg.host}:{cfg.port}\n\nJetzt senden?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            host, port, _size = self.adif_udp_service.send_qso(
                callsign=callsign, station_callsign=station_callsign, qso_at=qso_at,
                talkgroup=summary.last_talkgroup, timeslot=summary.last_timeslot,
                name=summary.name, country=summary.country,
            )
        except AdifUdpError as error:
            QMessageBox.warning(self, "ADIF-UDP", str(error))
            self.statusBar().showMessage(f"ADIF-UDP fehlgeschlagen: {error}")
            return
        self.statusBar().showMessage(f"ADIF-UDP: {callsign} an {host}:{port} gesendet.")
        QMessageBox.information(
            self, "ADIF-UDP",
            f"QSO mit {callsign} wurde an {host}:{port} gesendet.\n"
            "UDP bestätigt nur das lokale Senden; ob das Logbuch den Datensatz übernommen hat, zeigt das Empfängerprogramm."
        )

    def _history_qrz_status(self, summary) -> str:
        if not summary.worked_at or not summary.callsign:
            return ""
        logid = self.receive_service.history.qrz_logid(summary.callsign, summary.worked_at)
        return f"Gespeichert · LOGID {logid}" if logid else ""

    def _log_history_qso_to_qrz(self, summary) -> None:
        if self._qrz_log_pending:
            self.statusBar().showMessage("QRZ: Eine Übertragung läuft bereits.")
            return
        if not self.qrz_logbook_service.configured:
            QMessageBox.information(
                self, "QRZ.com Logbook",
                "QRZ.com Logbook ist noch nicht aktiviert oder der API Access Key fehlt. "
                "Bitte zuerst die Einstellungen öffnen."
            )
            return
        if not summary.worked or not summary.worked_at or not summary.callsign:
            self.statusBar().showMessage("QRZ: Nur bestätigte QSOs mit Rufzeichen können geloggt werden.")
            return
        try:
            qso_at = datetime.fromisoformat(summary.worked_at)
            station_callsign = self.station_settings.station_callsign()
        except Exception as error:
            QMessageBox.warning(
                self, "QRZ.com Logbook",
                f"QSO-Daten konnten nicht vorbereitet werden: {error}"
            )
            return
        callsign = summary.callsign.strip().upper()
        existing = self.receive_service.history.qrz_logid(callsign, summary.worked_at)
        if existing:
            QMessageBox.information(
                self, "QRZ.com Logbook",
                f"Dieses QSO wurde bereits übertragen. QRZ LOGID {existing}."
            )
            self.history_widget.refresh()
            return
        answer = QMessageBox.question(
            self, "QSO bei QRZ.com loggen",
            f"{callsign} · {qso_at.astimezone(timezone.utc).strftime('%d.%m.%Y %H:%M UTC')} · 70cm · DMR\n"
            f"BrandMeister TG {summary.last_talkgroup} · TS{summary.last_timeslot}\n\n"
            "Jetzt an QRZ.com senden?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._qrz_log_pending = True
        self.history_widget.qrz_log_button.setEnabled(False)
        self.statusBar().showMessage(f"QRZ: {callsign} wird übertragen …")
        source_id = summary.source_id
        worked_at = summary.worked_at
        tg = summary.last_talkgroup
        ts = summary.last_timeslot

        def worker() -> None:
            try:
                result = self.qrz_logbook_service.insert_dmr_qso(
                    callsign=callsign,
                    station_callsign=station_callsign,
                    qso_at=qso_at,
                    talkgroup=tg,
                    timeslot=ts,
                )
                self._updates.put(
                    ("qrz_log_ok", (source_id, callsign, worked_at, result.logid))
                )
            except QrzLogbookError as error:
                self._updates.put(("qrz_log_error", str(error)))

        Thread(target=worker, name="CarenDMR-QRZ-Logbook", daemon=True).start()

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
