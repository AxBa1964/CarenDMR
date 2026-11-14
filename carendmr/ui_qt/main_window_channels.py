"""Kanalwahl (Talkgroup, Timeslot, Rufart), Favoriten, Schnellwahl und TG-Monitor-Übernahme.

Teil von ``MainWindow`` (siehe main_window.py). Die Methoden wurden ab
0.2.1.87 unverändert aus dem Hauptfenster hierher verschoben.
"""
from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QMessageBox, QPushButton
from carendmr.application import RadioState
from carendmr.application.operating_preferences import OperatingPreferences
from carendmr.domain import DmrChannel


class MainWindowChannelsMixin:
    """Mixin für ``MainWindow``; setzt dessen Attribute voraus."""

    def _refresh_segment_style(self, button: QPushButton, selected: bool) -> None:
        """Visualisiert eine Auswahl, ohne dem Widget eine Checkbox-Rolle zu geben."""
        button.setProperty("selected", selected)
        button.style().unpolish(button)
        button.style().polish(button)

    def _sync_radio_controls(self) -> None:
        """Synchronisiert Auswahloptik, Fokuspfad und kurze Screenreader-Namen."""
        controls = (
            (self.ts1_radio, self._selected_timeslot == 1, "Timeslot 1"),
            (self.ts2_radio, self._selected_timeslot == 2, "Timeslot 2"),
            (self.group_radio, self._selected_call_type == "group", "Gruppenruf"),
            (self.private_radio, self._selected_call_type == "private", "Privatruf"),
        )
        for button, selected, label in controls:
            self._refresh_segment_style(button, selected)
            button.setProperty("radioFlag", True)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.setAccessibleName("")
            button.setAccessibleDescription("")
        if hasattr(self, "current_channel_meta_label"):
            call_text = "Gruppe" if self._selected_call_type == "group" else "Privat"
            self.current_channel_meta_label.setText(
                f"TS{self._selected_timeslot} · {call_text}"
            )
        if hasattr(self, "operation_gain_slider") and hasattr(self, "connect_button"):
            self._restore_tab_order()

    def _select_timeslot(self, timeslot: int, *, announce: bool = False) -> None:
        if timeslot not in {1, 2} or not self.radio_state.snapshot().can_edit_parameters:
            return
        self._selected_timeslot = timeslot
        self._sync_radio_controls()
        self._persist_current_target()
        if announce:
            self.accessibility.announce_timeslot(self.connection_label, timeslot)

    def _select_call_type(self, call_type: str, *, announce: bool = False) -> None:
        if call_type not in {"group", "private"} or not self.radio_state.snapshot().can_edit_parameters:
            return
        self._selected_call_type = call_type
        self._sync_radio_controls()
        self._persist_current_target()
        if announce:
            self.accessibility.announce_call_type(self.connection_label, call_type)

    def _persist_current_target(self) -> None:
        """Speichert TG, Timeslot und Rufart ohne den Fokusablauf zu verändern."""
        try:
            self._save_preferences()
        except Exception as error:
            self.statusBar().showMessage(f"DMR-Kanal konnte nicht gespeichert werden: {error}")

    def _target(self) -> tuple[int, int, str]:
        text = self.current_tg_label.text().strip()
        if not text or not text.isdigit() or int(text) <= 0:
            raise ValueError("Bitte eine gültige Talkgroup eingeben.")
        return int(text), self._selected_timeslot, self._selected_call_type

    def _update_talkgroup_accessibility(self, value: str) -> None:
        """Hält nur den zugänglichen Feldkontext aktuell, ohne Ansage."""
        spoken = self.accessibility.formatter.digits(value)
        description = f"Aktueller Wert, Ziffern {spoken}" if spoken else "Feld ist leer"
        self.tg_edit.setAccessibleDescription(description)

    def _announce_pending_talkgroup(self) -> None:
        value = self.tg_edit.text().strip()
        if value:
            self.accessibility.announce_pending_talkgroup(self.tg_edit, value)

    def _focus_talkgroup(self) -> None:
        """Setzt nach dem Trennen den Fokus in das Feld für eine neue Talkgroup."""
        self.tg_edit.setFocus()
        self.tg_edit.selectAll()

    def _focus_ptt_after_connect(self, retries: int = 12) -> None:
        """Setzt nach erfolgreichem Verbinden den Fokus zuverlässig auf PTT.

        Die Encoder-Prüfung kann wenige Millisekunden später fertig werden.
        Solange der Button noch gesperrt ist, wird deshalb kurz erneut versucht.
        """
        if self.radio_state.state is not RadioState.CONNECTED:
            return
        if self.ptt_button.isEnabled():
            self.ptt_button.setFocus(Qt.FocusReason.ShortcutFocusReason)
            return
        if retries > 0:
            QTimer.singleShot(100, lambda: self._focus_ptt_after_connect(retries - 1))

    def _restore_saved_dmr_channel(self) -> None:
        """Stellt den zuletzt gespeicherten DMR-Kanal vollständig wieder her.

        Der gespeicherte Zustand enthält nur Ziel, Timeslot und Rufart. Der
        Anzeigename wird deshalb beim Start erneut aus dem lokalen
        Talkgroup-Verzeichnis aufgelöst. Unbekannte Ziele bleiben namenlos.
        """
        known = self._known_channel_for_target(self.preferences.talkgroup)
        channel = DmrChannel(
            target=self.preferences.talkgroup,
            timeslot=self.preferences.timeslot,
            call_type=self.preferences.call_type,
            name=known.name if known else "",
            country=known.country if known else "",
            description=known.description if known else "",
        )
        self._set_current_dmr_channel(channel, clear_input=False)

    def _known_channel_for_target(self, target: int):
        """Liefert den ersten bekannten Kanal für eine Zielnummer oder ``None``."""
        for channel in self.talkgroup_search_service.channels:
            if channel.target == target:
                return channel.normalized()
        return None

    def _set_current_dmr_channel(self, channel, *, clear_input: bool = True) -> None:
        """Aktualisiert den aktuell gewählten DMR-Kanal immer vollständig.

        Diese Methode ist die einzige Quelle für TG, Name, Timeslot und Rufart
        auf der Betriebsseite. Dadurch bleiben Suche, manuelle Eingabe und
        spätere Favoriten synchron.
        """
        normalized = channel.normalized()
        previous = self._current_dmr_channel
        if (
            previous is not None
            and self.qso_recording_service.is_active
            and (previous.target, previous.timeslot, previous.call_type)
                != (normalized.target, normalized.timeslot, normalized.call_type)
        ):
            self._stop_qso_recording("Mitschnitt wegen Zielwechsel beendet")
        self._current_dmr_channel = normalized
        self.current_tg_label.setText(str(normalized.target))
        self.current_tg_name_label.setText(normalized.name or "")
        self._selected_timeslot = normalized.timeslot
        self._selected_call_type = normalized.call_type
        self._sync_radio_controls()
        if clear_input:
            self.tg_edit.clear()
            self._update_talkgroup_accessibility("")
        if hasattr(self, "favorite_button"):
            self._update_favorite_button()

    def _update_known_talkgroup_name(self, value: str) -> None:
        """Aktualisiert den Namen zur bereits übernommenen aktuellen TG."""
        text = str(value).strip()
        channel = self._known_channel_for_target(int(text)) if text.isdigit() else None
        self.current_tg_name_label.setText(channel.name if channel else "")

    def _refresh_favorites(self) -> None:
        """Aktualisiert nur Favoriten-Metadaten der gemeinsamen Kanalliste.

        Der Audio-Benchmark ist eine langlebige Hauptfenster-Komponente. Er darf
        beim Aktualisieren der Favoriten nicht neu erzeugt werden, weil das
        Benchmark-Widget sonst am alten Service hängt, während der RX-Pfad den
        neuen Service beliefert.
        """
        self.talkgroup_search_service.set_favorites(self.favorite_service.favorites)
        if hasattr(self, "favorites_widget"):
            self.favorites_widget.refresh()
        self._update_favorite_button()
        self._refresh_favorite_hot_buttons()
        self._refresh_favorite_combo()

    def _refresh_favorite_combo(self) -> None:
        if not hasattr(self, "favorite_combo"):
            return
        combo = self.favorite_combo
        combo.blockSignals(True)
        try:
            combo.clear()
            combo.addItem("Alle Favoriten …", None)
            for favorite in self.favorite_service.favorites:
                kind = "G" if favorite.call_type == "group" else "P"
                text = f"{favorite.display_name}  ·  TG {favorite.target} / TS{favorite.timeslot} / {kind}"
                combo.addItem(text, favorite)
            combo.setCurrentIndex(0)
            combo.setEnabled(len(self.favorite_service.favorites) > 0)
        finally:
            combo.blockSignals(False)

    def _favorite_combo_selected(self, index: int) -> None:
        if index <= 0:
            return
        favorite = self.favorite_combo.itemData(index)
        self.favorite_combo.blockSignals(True)
        self.favorite_combo.setCurrentIndex(0)
        self.favorite_combo.blockSignals(False)
        if favorite is None:
            return
        self._activate_favorite(favorite, source_label="Favorit")

    def _activate_favorite(self, favorite, *, source_label: str) -> None:
        if self._tx_active or self._tx_pending or self._tx_stopping:
            self.statusBar().showMessage(f"{source_label} ist während TX nicht möglich.")
            return
        channel = favorite.to_dmr_channel()
        state = self.radio_state.state
        if state in {RadioState.CONNECTING, RadioState.DISCONNECTING}:
            self.statusBar().showMessage(
                f"{source_label} wartet, bis der aktuelle Verbindungswechsel beendet ist."
            )
            return
        if state is RadioState.CONNECTED:
            self._pending_hot_favorite = channel
            self.statusBar().showMessage(
                f"{source_label} {favorite.display_name}: trenne aktuelle Verbindung …"
            )
            self._disconnect()
            return
        self._connect_hot_favorite(channel)

    def _refresh_favorite_hot_buttons(self) -> None:
        if not hasattr(self, "favorite_hot_buttons"):
            return
        favorites = self.favorite_service.favorites[:3]
        for index, button in enumerate(self.favorite_hot_buttons):
            if index >= len(favorites):
                button.setText("–")
                button.setEnabled(False)
                button.setToolTip("Kein Favorit an dieser Position")
                continue
            favorite = favorites[index]
            kind = "G" if favorite.call_type == "group" else "P"
            name = favorite.display_name
            # Kurzer sichtbarer Name; alle technischen Werte bleiben im Tooltip/AccessibleName.
            button.setText(name)
            detail = f"TG {favorite.target} · TS{favorite.timeslot} · {kind}"
            button.setToolTip(detail)
            button.setAccessibleName(f"Schnellwahl {index + 1}: {name}, {detail}")
            button.setEnabled(True)

    def _activate_hot_favorite(self, index: int) -> None:
        favorites = self.favorite_service.favorites
        if not 0 <= index < min(3, len(favorites)):
            return
        self._activate_favorite(favorites[index], source_label="Schnellwahl")

    def _connect_hot_favorite(self, channel) -> None:
        try:
            normalized = channel.normalized()
        except (AttributeError, TypeError, ValueError):
            self._pending_hot_favorite = None
            return
        self._set_current_dmr_channel(normalized)
        try:
            self._save_preferences()
        except Exception as error:
            self._pending_hot_favorite = None
            QMessageBox.warning(self, "CarenDMR", str(error))
            return
        self._pending_hot_favorite = None
        self.tabs.setCurrentIndex(0)
        self.statusBar().showMessage(
            f"Schnellwahl {normalized.name or normalized.target}: verbinde TG {normalized.target}, "
            f"TS{normalized.timeslot}, {'Gruppe' if normalized.is_group_call else 'Privat'} …"
        )
        self._connect()

    def _handle_external_channel_request(self, channel: DmrChannel) -> tuple[bool, str]:
        """Übernimmt einen Kanal aus dem eigenständigen TG-Monitor."""
        try:
            normalized = channel.normalized()
        except (AttributeError, TypeError, ValueError) as error:
            return False, f"Ungültiger DMR-Kanal: {error}"

        if self._tx_active or self._tx_pending or self._tx_stopping:
            return False, "CarenDMR sendet gerade. Kanalwechsel wurde nicht ausgeführt."

        state = self.radio_state.state
        if state in {RadioState.CONNECTING, RadioState.DISCONNECTING}:
            return False, "CarenDMR wechselt gerade die Verbindung. Bitte gleich erneut versuchen."

        if state is RadioState.CONNECTED:
            self._pending_external_channel = normalized
            self.statusBar().showMessage(f"TG-Monitor: trenne für TG {normalized.target} …")
            self._disconnect()
            return True, f"TG {normalized.target} wird in CarenDMR übernommen."

        if state in {RadioState.DISCONNECTED, RadioState.ERROR}:
            QTimer.singleShot(0, lambda selected=normalized: self._connect_external_channel(selected))
            return True, f"TG {normalized.target} wird in CarenDMR übernommen."

        return False, "CarenDMR ist momentan nicht bereit für einen Kanalwechsel."

    def _connect_external_channel(self, channel: DmrChannel) -> None:
        try:
            normalized = channel.normalized()
        except (AttributeError, TypeError, ValueError):
            self._pending_external_channel = None
            return

        if self._tx_active or self._tx_pending or self._tx_stopping:
            self._pending_external_channel = None
            self.statusBar().showMessage("TG-Monitor-Kanalwechsel wegen TX verworfen.")
            return
        if self.radio_state.state not in {RadioState.DISCONNECTED, RadioState.ERROR}:
            return

        self._set_current_dmr_channel(normalized)
        try:
            self._save_preferences()
        except Exception as error:
            self._pending_external_channel = None
            QMessageBox.warning(self, "CarenDMR", str(error))
            return

        self._pending_external_channel = None
        self.tabs.setCurrentIndex(0)
        self.statusBar().showMessage(
            f"TG-Monitor: verbinde TG {normalized.target}, TS{normalized.timeslot}, "
            f"{'Gruppe' if normalized.is_group_call else 'Privat'} …"
        )
        self._connect()

    def _update_favorite_button(self) -> None:
        if not hasattr(self, "favorite_button") or self._current_dmr_channel is None:
            return
        channel = self._current_dmr_channel
        favorite = self.favorite_service.find(channel.target, channel.timeslot, channel.call_type)
        self.favorite_button.setText("★" if favorite else "☆")
        action = "bearbeiten" if favorite else "speichern"
        self.favorite_button.setAccessibleName(f"Aktuellen DMR-Kanal als Favorit {action}")

    def _edit_current_favorite(self) -> None:
        channel = self._current_dmr_channel
        if channel is None:
            return
        if self.favorites_widget.add_channel(channel):
            self._refresh_favorites()
            self.statusBar().showMessage("Favorit gespeichert.")

    def _apply_favorite_channel(self, channel) -> None:
        self._apply_selected_channel(channel)
        self.tabs.setCurrentIndex(0)
        self.connect_button.setFocus()

    def _apply_selected_channel(self, channel) -> None:
        """Übernimmt einen Treffer vollständig als DMR-Kanal, ohne zu verbinden."""
        try:
            normalized = channel.normalized()
        except (AttributeError, TypeError, ValueError):
            return
        if not self.radio_state.snapshot().can_edit_parameters:
            return
        self._set_current_dmr_channel(normalized)
        try:
            self._save_preferences()
        except Exception as error:
            QMessageBox.warning(self, "CarenDMR", str(error))
            return
        self.connect_button.setFocus()
        target_kind = "Talkgroup" if normalized.is_group_call else "DMR-ID"
        channel_name = f" {normalized.name}" if normalized.name else ""
        self.statusBar().showMessage(
            f"{target_kind}{channel_name} {normalized.target}, TS{normalized.timeslot}, "
            f"{'Gruppe' if normalized.is_group_call else 'Privat'} übernommen."
        )

    def _apply_pending_talkgroup(self) -> bool:
        """Übernimmt eine eingetragene neue TG, bevor verbunden wird."""
        if not self.tg_edit.text().strip():
            return True
        return self._apply_talkgroup_entry()

    def _apply_talkgroup_entry(self) -> bool:
        """Übernimmt die neue TG; Enter stellt noch keine Verbindung her."""
        text = self.tg_edit.text().strip()
        if not text:
            return True
        if not text.isdigit() or int(text) <= 0:
            QMessageBox.warning(self, "CarenDMR", "Bitte eine gültige Talkgroup eingeben.")
            return False
        target = int(text)
        known = self._known_channel_for_target(target)
        if known is None:
            known = DmrChannel(target, self._selected_timeslot, self._selected_call_type)
        else:
            # Manuelle Nummerneingabe ändert TS und Rufart nicht heimlich.
            known = DmrChannel(
                known.target,
                self._selected_timeslot,
                self._selected_call_type,
                known.name,
                known.country,
                known.description,
            )
        self._set_current_dmr_channel(known)
        try:
            self._save_preferences()
        except Exception as error:
            QMessageBox.warning(self, "CarenDMR", str(error))
            return False
        self.connect_button.setFocus()
        self.statusBar().showMessage(f"Talkgroup {self.current_tg_label.text()} übernommen.")
        return True

    def _save_preferences(self) -> None:
        tg, ts, call_type = self._target()
        self.preferences_store.save(OperatingPreferences(tg, ts, call_type, False, self.preferences.screenreader_ptt_lead_in_seconds))
        self.preferences = self.preferences_store.load()
        self._selected_timeslot = self.preferences.timeslot
        self._selected_call_type = self.preferences.call_type

    def _toggle_timeslot(self) -> None:
        self._select_timeslot(2 if self._selected_timeslot == 1 else 1, announce=True)

    def _toggle_call_type(self) -> None:
        self._select_call_type("private" if self._selected_call_type == "group" else "group", announce=True)
