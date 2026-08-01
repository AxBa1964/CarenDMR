"""Anwendungsschicht für den vorhandenen rein empfangenden TG91-Betrieb."""

from __future__ import annotations

from pathlib import Path
from threading import Event, Lock, Thread
from typing import Callable

from carendmr.brandmeister.config import BrandMeisterConfigStore
from carendmr.brandmeister.listen import LiveListenProgress, LiveListenResult, listen_receive_only
from carendmr.domain import ConnectionState, EventLevel, ReceiveStatistics

from .event_service import EventService
from .state_store import ApplicationStateStore


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
            self.events.publish("Empfang auf Talkgroup 91, Timeslot 2 gestartet.")
        self.state_store.update(
            connection=ConnectionState.RECEIVING,
            brandmeister_connected=True,
            receive_active=True,
            audio_active=True,
            message="Empfang aktiv",
            statistics=statistics,
        )

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
                progress_interval=1.0,
                stop_requested=self._stop.is_set,
            )
            self._apply_result(result)
        except Exception as error:
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
