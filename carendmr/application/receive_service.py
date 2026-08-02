"""Anwendungsschicht für den vorhandenen rein empfangenden TG91-Betrieb."""

from __future__ import annotations

from pathlib import Path
from threading import Event, Lock, Thread
from typing import Callable

from carendmr.brandmeister.config import BrandMeisterConfigStore
from carendmr.brandmeister.listen import (
    LiveCallActivity, LiveListenProgress, LiveListenResult, listen_receive_only,
)
from carendmr.domain import ConnectionState, EventLevel, ReceiveStatistics

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
        self._connected_event_published = False
        self._capture_muted = Event()
        self._user_muted = Event()
        self._output_volume_percent = 100
        self._agc_enabled = True
        self._output_level_percent = 0.0
        self._output_level_callback: Callable[[float], None] | None = None
        self.contacts = ContactService(self.project_root)
        self.history = QsoHistoryService(self.project_root)
        self.current_calls = CurrentCallService(
            self.state_store, self.events, contact_lookup=self.contacts.lookup,
            on_finished=self.history.add_completed_call,
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
        if not self.is_running:
            return
        self.state_store.update(
            connection=ConnectionState.STOPPING,
            message="Empfang wird beendet",
        )
        self.events.publish("Empfang wird beendet.")
        self._stop.set()

    def wait(self, timeout: float | None = None) -> bool:
        with self._lock:
            thread = self._thread
        if thread is None:
            return True
        thread.join(timeout)
        return not thread.is_alive()

    def _on_progress(self, progress: LiveListenProgress) -> None:
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
        if not self._connected_event_published:
            self._connected_event_published = True
            self.events.publish("Anmeldung bei BrandMeister erfolgreich.")
            self.events.publish("Empfang auf Talkgroup 91 gestartet; eingehende Timeslots 1 und 2 werden verarbeitet.")
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
            )
            self.events.publish("Verbindung zu BrandMeister wird hergestellt.")
            result = self._listen(
                config,
                seconds=seconds,
                progress_callback=self._on_progress,
                call_activity_callback=self._on_call_activity,
                progress_interval=1.0,
                stop_requested=self._stop.is_set,
                output_muted=lambda: self.audio_output_muted,
                output_volume=lambda: self.output_volume_factor,
                output_agc_enabled=lambda: self.agc_enabled,
                output_level_callback=self._on_output_level,
            )
            self.current_calls.finish()
            self._apply_result(result)
        except Exception as error:
            self.current_calls.finish()
            self.state_store.update(
                connection=ConnectionState.ERROR,
                brandmeister_connected=False,
                receive_active=False,
                audio_active=False,
                message=str(error),
            )
            self.events.publish(
                f"Empfang abgebrochen: {type(error).__name__}: {error}",
                EventLevel.ERROR,
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
            state = ConnectionState.DISCONNECTED
            message = "Empfang beendet"
            self.events.publish("Empfang und Verbindung wurden sauber beendet.")
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
