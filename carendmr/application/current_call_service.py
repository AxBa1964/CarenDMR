"""Anwendungslogik für Sprechbeginn, Sprecherwechsel und Sprechende."""

from __future__ import annotations

from threading import Lock
from time import monotonic
from typing import Callable

from carendmr.domain import CurrentCall, RadioContact

from .event_service import EventService
from .state_store import ApplicationStateStore


class CurrentCallService:
    """Verwaltet genau einen aktiven Sprechdurchgang."""

    def __init__(
        self,
        state_store: ApplicationStateStore,
        events: EventService,
        *,
        clock: Callable[[], float] = monotonic,
        contact_lookup: Callable[[int], RadioContact | None] | None = None,
        on_finished: Callable[[CurrentCall], None] | None = None,
    ) -> None:
        self._state_store = state_store
        self._events = events
        self._clock = clock
        self._contact_lookup = contact_lookup or (lambda _dmr_id: None)
        self._on_finished = on_finished
        self._current: CurrentCall | None = None
        self._started_at: float | None = None
        self._lock = Lock()

    def start(
        self,
        *,
        source_id: int,
        talkgroup: int,
        timeslot: int,
        stream_id: int | None,
    ) -> CurrentCall:
        if source_id <= 0:
            raise ValueError("Die DMR-ID des Sprechers muss größer als null sein.")

        with self._lock:
            current = self._current
            if (
                current is not None
                and current.source_id == source_id
                and current.stream_id == stream_id
            ):
                return current

            previous = self._finish_locked(publish=True)
            del previous
            contact = self._contact_lookup(source_id)
            call = CurrentCall(source_id, talkgroup, timeslot, stream_id, contact=contact)
            self._current = call
            self._started_at = self._clock()

        self._state_store.update(current_call=call)
        identity = call.contact.callsign if call.contact else f"DMR-ID {source_id}"
        name = call.contact.display_name if call.contact else ""
        details = f" ({name})" if name else ""
        self._events.publish(
            f"{identity}{details} spricht auf Talkgroup {talkgroup}, Timeslot {timeslot}."
        )
        return call

    def update_duration(self) -> CurrentCall | None:
        with self._lock:
            if self._current is None or self._started_at is None:
                return None
            updated = self._current.with_elapsed(self._clock() - self._started_at)
            self._current = updated
        self._state_store.update(current_call=updated)
        return updated

    def finish(self) -> CurrentCall | None:
        with self._lock:
            finished = self._finish_locked(publish=False)
        if finished is None:
            return None
        self._state_store.update(current_call=None)
        identity = finished.contact.callsign if finished.contact else f"DMR-ID {finished.source_id}"
        self._events.publish(
            f"Sprechdurchgang von {identity} beendet "
            f"({finished.elapsed_seconds:.0f} Sekunden)."
        )
        if self._on_finished is not None:
            self._on_finished(finished)
        return finished

    def _finish_locked(self, *, publish: bool) -> CurrentCall | None:
        if self._current is None:
            return None
        elapsed = 0.0
        if self._started_at is not None:
            elapsed = max(0.0, self._clock() - self._started_at)
        finished = self._current.with_elapsed(elapsed)
        self._current = None
        self._started_at = None
        if publish:
            self._state_store.update(current_call=None)
            identity = finished.contact.callsign if finished.contact else f"DMR-ID {finished.source_id}"
            self._events.publish(
                f"Sprechdurchgang von {identity} beendet "
                f"({finished.elapsed_seconds:.0f} Sekunden)."
            )
            if self._on_finished is not None:
                self._on_finished(finished)
        return finished
