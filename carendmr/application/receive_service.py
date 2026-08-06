"""Anwendungsschicht für dynamischen Talkgroup-Empfang ohne BrandMeister-API."""

from __future__ import annotations

from pathlib import Path
from threading import Event, Lock, Thread
from typing import Callable

from carendmr.brandmeister.config import BrandMeisterConfigStore
from carendmr.brandmeister.dynamic_subscription import validate_receive_target
from carendmr.brandmeister.listen import (
    LiveCallActivity, LiveListenProgress, LiveListenResult, listen_receive_only,
)
from carendmr.domain import (ConnectionState, EventLevel, ReceiveStatistics, InformationCategory, InformationPriority)
from carendmr.diagnostics.tx_rx_timing import mark as timing_mark

from .contact_service import ContactService
from .current_call_service import CurrentCallService
from .event_service import EventService
from .state_store import ApplicationStateStore
from .qso_history_service import QsoHistoryService


class ReceiveService:
    """Steuert den Empfang, ohne der GUI technische Details offenzulegen."""

    def __init__(
        self,
        project_root: Path,
        *,
        state_store: ApplicationStateStore | None = None,
        events: EventService | None = None,
        listen_function: Callable[..., LiveListenResult] = listen_receive_only,
    ) -> None:
        self.project_root = Path(project_root)
        self.state_store = state_store or ApplicationStateStore()
        self.events = events or EventService()
        self._listen = listen_function
        self._stop = Event()
        self._thread: Thread | None = None
        self._lock = Lock()
        self._switch_lock = Lock()
        self._switch_thread: Thread | None = None
        self._switch_cancel = Event()
        self._connected_event_published = False
        self._capture_muted = Event()
        self._user_muted = Event()
        self._output_volume_percent = 100
        self._agc_enabled = True
        self._output_level_percent = 0.0
        self._target_talkgroup = 91
        self._target_timeslot = 2
        self._target_call_type = "group"
        self._output_level_callback: Callable[[float], None] | None = None
        self._audio_debug_enabled = False
        self._decoded_pcm_callback = None
        self._connection_lost_callback = None
        self._connection_restored_callback = None
        self._call_activity_observer = None
        self._audio_debug_dir_provider = None
        self.contacts = ContactService(self.project_root)
        self.history = QsoHistoryService(self.project_root)
        self.current_calls = CurrentCallService(
            self.state_store, self.events, contact_lookup=self.contacts.lookup,
            on_finished=self.history.add_completed_call,
        )


    def set_call_activity_observer(self, callback) -> None:
        self._call_activity_observer = callback

    def set_decoded_pcm_callback(self, callback) -> None:
        self._decoded_pcm_callback = callback

    def set_connection_callbacks(self, *, lost=None, restored=None) -> None:
        self._connection_lost_callback = lost
        self._connection_restored_callback = restored

    def set_audio_debug_dir_provider(self, provider) -> None:
        self._audio_debug_dir_provider = provider

    def set_audio_debug_enabled(self, enabled: object) -> bool:
        self._audio_debug_enabled = bool(enabled)
        return self._audio_debug_enabled

    def set_receive_target(self, talkgroup: int, timeslot: int, call_type: str = "group") -> None:
        talkgroup, timeslot = validate_receive_target(talkgroup, timeslot)
        call_type = str(call_type).strip().lower()
        if call_type not in {"group", "private"}:
            raise ValueError("Die Rufart muss group oder private sein.")
        if self.is_running:
            raise RuntimeError("Die Talkgroup kann nur bei getrenntem Empfang direkt geändert werden.")
        self._target_talkgroup = talkgroup
        self._target_timeslot = timeslot
        self._target_call_type = call_type
        self.state_store.update(talkgroup=talkgroup, timeslot=timeslot)

    @property
    def target_talkgroup(self) -> int:
        return self._target_talkgroup

    @property
    def target_timeslot(self) -> int:
        return self._target_timeslot

    @property
    def target_call_type(self) -> str:
        return self._target_call_type

    @property
    def is_switching(self) -> bool:
        with self._switch_lock:
            return self._switch_thread is not None and self._switch_thread.is_alive()

    def switch_receive_target(self, talkgroup: int, timeslot: int, call_type: str = "group") -> bool:
        """Wechselt TG und Timeslot automatisch und startet den Empfang erneut."""
        talkgroup, timeslot = validate_receive_target(talkgroup, timeslot)
        call_type = str(call_type).strip().lower()
        if call_type not in {"group", "private"}:
            raise ValueError("Die Rufart muss group oder private sein.")
        with self._switch_lock:
            if self._switch_thread is not None and self._switch_thread.is_alive():
                return False
            self._switch_cancel.clear()
            self._switch_thread = Thread(
                target=self._switch_worker,
                args=(talkgroup, timeslot, call_type),
                name="CarenDMR-Receive-Switch",
                daemon=True,
            )
            self._switch_thread.start()
        return True

    def _switch_worker(self, talkgroup: int, timeslot: int, call_type: str) -> None:
        old_tg = self._target_talkgroup
        old_ts = self._target_timeslot
        self.events.publish(
            f"Empfang wird von Talkgroup {old_tg}, Timeslot {old_ts} "
            f"auf Talkgroup {talkgroup}, Timeslot {timeslot} umgeschaltet."
        )
        if self.is_running:
            self._request_stop(cancel_pending_switch=False, message="Empfang wird für TG-/TS-Wechsel beendet")
            if not self.wait(8.0):
                self.events.publish(
                    "TG-/TS-Wechsel abgebrochen: Der bisherige Empfang wurde nicht rechtzeitig beendet.",
                    EventLevel.ERROR,
                )
                return
        if self._switch_cancel.is_set():
            self.events.publish("TG-/TS-Wechsel wurde abgebrochen.")
            return
        self.set_receive_target(talkgroup, timeslot, call_type)
        if not self.start():
            self.events.publish(
                "TG-/TS-Wechsel abgebrochen: Der neue Empfang konnte nicht gestartet werden.",
                EventLevel.ERROR,
            )
            return
        self.events.publish(
            f"Automatischer Wechsel auf Talkgroup {talkgroup}, Timeslot {timeslot} gestartet."
        )

    def mute_audio_output(self) -> None:
        """Unterdrückt nur die lokale Empfangswiedergabe; Netzwerk und Decoder laufen weiter."""
        self._capture_muted.set()

    def unmute_audio_output(self) -> None:
        self._capture_muted.clear()

    def set_user_muted(self, muted: bool) -> None:
        if muted:
            self._user_muted.set()
        else:
            self._user_muted.clear()

    def set_output_volume_percent(self, value: int) -> None:
        self._output_volume_percent = max(0, min(400, int(value)))

    def set_agc_enabled(self, enabled: bool) -> None:
        self._agc_enabled = bool(enabled)

    def set_output_level_callback(self, callback: Callable[[float], None] | None) -> None:
        self._output_level_callback = callback

    def _on_output_level(self, level: float) -> None:
        self._output_level_percent = max(0.0, min(100.0, float(level)))
        if self._output_level_callback is not None:
            self._output_level_callback(self._output_level_percent)

    @property
    def audio_output_muted(self) -> bool:
        return self._capture_muted.is_set() or self._user_muted.is_set()

    @property
    def output_volume_factor(self) -> float:
        return self._output_volume_percent / 100.0

    @property
    def agc_enabled(self) -> bool:
        return self._agc_enabled

    @property
    def output_level_percent(self) -> float:
        return self._output_level_percent

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._thread is not None and self._thread.is_alive()

    def start(self, *, seconds: float | None = None) -> bool:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return False
            self._stop.clear()
            self._connected_event_published = False
            self.current_calls = CurrentCallService(
                self.state_store, self.events, contact_lookup=self.contacts.lookup,
                on_finished=self.history.add_completed_call,
            )
            self._thread = Thread(
                target=self._run,
                kwargs={"seconds": seconds},
                name="CarenDMR-Receive",
                daemon=True,
            )
            self._thread.start()
        return True

    def stop(self) -> None:
        self._request_stop(cancel_pending_switch=True, message="Empfang wird beendet")

    def _request_stop(self, *, cancel_pending_switch: bool, message: str) -> None:
        if cancel_pending_switch:
            self._switch_cancel.set()
        if not self.is_running:
            return
        self.state_store.update(
            connection=ConnectionState.STOPPING,
            message=message,
        )
        self.events.publish(f"{message}.")
        self._stop.set()

    def wait(self, timeout: float | None = None) -> bool:
        with self._lock:
            thread = self._thread
        if thread is None:
            return True
        thread.join(timeout)
        return not thread.is_alive()

    def _on_connected(self) -> None:
        """Meldet RX unmittelbar nach Login und Zielaktivierung als bereit."""
        if self._connected_event_published:
            return
        self._connected_event_published = True
        if self._connection_restored_callback is not None:
            self._connection_restored_callback()
        timing_mark("RX_VERBUNDEN_STATUS", "Direkt nach BM-Anmeldung und Zielaktivierung")
        self.events.publish(
            "Anmeldung bei BrandMeister erfolgreich.",
            code="connection.connected",
            long_text="Mit BrandMeister verbunden.",
            category=InformationCategory.CONNECTION,
            priority=InformationPriority.HIGH,
        )
        self.events.publish(
            f"Empfang auf Talkgroup {self._target_talkgroup}, Timeslot {self._target_timeslot} gestartet.",
            code="reception.active",
            long_text=(
                f"Empfang aktiv. Talkgroup {self._target_talkgroup}, "
                f"Timeslot {self._target_timeslot}, "
                f"{'Privatruf' if self._target_call_type == 'private' else 'Gruppenruf'}."
            ),
            category=InformationCategory.RECEPTION,
            priority=InformationPriority.HIGH,
        )
        self.state_store.update(
            connection=ConnectionState.RECEIVING,
            brandmeister_connected=True,
            receive_active=True,
            audio_active=True,
            message="Empfang aktiv",
        )

    def _on_progress(self, progress: LiveListenProgress) -> None:
        # Fallback für ältere bzw. gemockte Listen-Funktionen, die den neuen
        # connected_callback noch nicht auslösen.
        self._on_connected()
        statistics = ReceiveStatistics(
            elapsed_seconds=progress.elapsed_seconds,
            datagrams=progress.datagrams,
            voice_bursts=progress.target_voice_bursts,
            decoded_codewords=progress.decoded_codewords,
            decode_errors=progress.decode_errors,
            corrected_errors=progress.corrected_errors,
            concealed_bursts=progress.concealed_bursts,
            invalid_dmrd=progress.invalid_dmrd,
        )
        self.current_calls.update_duration()
        self.state_store.update(
            connection=ConnectionState.RECEIVING,
            brandmeister_connected=True,
            receive_active=True,
            audio_active=True,
            message="Empfang aktiv",
            statistics=statistics,
        )

    def _on_call_activity(self, activity: LiveCallActivity) -> None:
        if self._call_activity_observer is not None:
            self._call_activity_observer(activity)
        if activity.active:
            self.current_calls.start(
                source_id=activity.source_id,
                talkgroup=activity.talkgroup,
                timeslot=activity.timeslot,
                stream_id=activity.stream_id,
            )
        else:
            self.current_calls.finish()

    def _run(self, *, seconds: float | None) -> None:
        try:
            path = self.project_root / "config" / "brandmeister.local.json"
            config = BrandMeisterConfigStore(path).load()
            self.state_store.update(
                connection=ConnectionState.CONNECTING,
                server=f"{config.host}:{config.port}",
                brandmeister_connected=False,
                receive_active=False,
                audio_active=False,
                message="Verbindung wird hergestellt",
                talkgroup=self._target_talkgroup,
                timeslot=self._target_timeslot,
            )
            self.events.publish(
                "Verbindung zu BrandMeister wird hergestellt.",
                code="connection.connecting",
                long_text="Verbindung zu BrandMeister wird hergestellt. Bitte warten.",
                category=InformationCategory.CONNECTION,
                priority=InformationPriority.HIGH,
            )
            timing_mark("RX_VERBINDUNGSAUFBAU_START", f"{config.host}:{config.port}")
            result = self._listen(
                config,
                seconds=seconds,
                target_talkgroup=self._target_talkgroup,
                target_timeslot=self._target_timeslot,
                target_call_type=self._target_call_type,
                progress_callback=self._on_progress,
                call_activity_callback=self._on_call_activity,
                connected_callback=self._on_connected,
                progress_interval=1.0,
                stop_requested=self._stop.is_set,
                output_muted=lambda: self.audio_output_muted,
                output_volume=lambda: self.output_volume_factor,
                output_agc_enabled=lambda: self.agc_enabled,
                output_level_callback=self._on_output_level,
                decoded_pcm_callback=self._decoded_pcm_callback,
                audio_debug_dir=(self._audio_debug_dir_provider if self._audio_debug_dir_provider is not None else (self.project_root / "logs" / "audio_lab")) if self._audio_debug_enabled else None,
            )
            self.current_calls.finish()
            self._apply_result(result)
        except Exception as error:
            self.current_calls.finish()
            if self._connection_lost_callback is not None:
                self._connection_lost_callback()
            self.state_store.update(
                connection=ConnectionState.ERROR,
                brandmeister_connected=False,
                receive_active=False,
                audio_active=False,
                message=str(error),
            )
            self.events.publish(
                f"Empfang abgebrochen: {type(error).__name__}: {error}",
                EventLevel.ERROR, code="connection.error",
                long_text=(
                    "Die Verbindung zu BrandMeister wurde wegen eines Fehlers beendet. "
                    "Empfang und Senden sind derzeit nicht möglich."
                ),
                category=InformationCategory.ERROR,
                priority=InformationPriority.ERROR,
                action_hint="Netzwerk und BrandMeister-Einstellungen prüfen und erneut verbinden.",
            )

    def _apply_result(self, result: LiveListenResult) -> None:
        statistics = ReceiveStatistics(
            elapsed_seconds=result.elapsed_seconds,
            datagrams=result.datagrams,
            voice_bursts=result.target_voice_bursts,
            decoded_codewords=result.decoded_codewords,
            decode_errors=result.decode_errors,
            corrected_errors=result.corrected_errors,
            concealed_bursts=result.concealed_bursts,
            invalid_dmrd=result.invalid_dmrd,
        )
        if result.closed:
            timing_mark("RX_SOCKET_AUDIO_GESCHLOSSEN")
            state = ConnectionState.DISCONNECTED
            message = "Empfang beendet"
            self.events.publish(
                "Empfang und Verbindung beendet.",
                code="connection.disconnected",
                long_text="Empfang und Verbindung zu BrandMeister wurden beendet.",
                category=InformationCategory.CONNECTION,
                priority=InformationPriority.HIGH,
            )
        else:
            state = ConnectionState.ERROR
            message = "Empfang konnte nicht sauber beendet werden"
            self.events.publish(message, EventLevel.ERROR)
        self.state_store.update(
            connection=state,
            brandmeister_connected=False,
            receive_active=False,
            audio_active=False,
            message=message,
            statistics=statistics,
        )
