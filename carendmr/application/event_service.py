"""Thread-sicheres Ereignisprotokoll für Konsole und GUI."""

from __future__ import annotations

from collections import deque
from datetime import datetime
from threading import Lock
from typing import Callable

from carendmr.domain import ApplicationEvent, EventLevel


class EventService:
    def __init__(self, *, maximum: int = 500) -> None:
        if maximum < 1:
            raise ValueError("Das Ereignisprotokoll benötigt mindestens einen Eintrag.")
        self._events: deque[ApplicationEvent] = deque(maxlen=maximum)
        self._listeners: list[Callable[[ApplicationEvent], None]] = []
        self._lock = Lock()

    def subscribe(self, listener: Callable[[ApplicationEvent], None]) -> None:
        with self._lock:
            self._listeners.append(listener)

    def publish(self, message: str, level: EventLevel = EventLevel.INFO) -> ApplicationEvent:
        event = ApplicationEvent(datetime.now(), message, level)
        with self._lock:
            self._events.append(event)
            listeners = tuple(self._listeners)
        for listener in listeners:
            listener(event)
        return event

    def snapshot(self) -> tuple[ApplicationEvent, ...]:
        with self._lock:
            return tuple(self._events)
