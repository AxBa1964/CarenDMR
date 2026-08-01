"""Thread-sicherer, beobachtbarer Anwendungszustand."""

from __future__ import annotations

from threading import Lock
from typing import Callable

from carendmr.domain import ApplicationState


class ApplicationStateStore:
    def __init__(self) -> None:
        self._state = ApplicationState()
        self._listeners: list[Callable[[ApplicationState], None]] = []
        self._lock = Lock()

    def get(self) -> ApplicationState:
        with self._lock:
            return self._state

    def subscribe(self, listener: Callable[[ApplicationState], None]) -> None:
        with self._lock:
            self._listeners.append(listener)

    def update(self, **changes: object) -> ApplicationState:
        with self._lock:
            self._state = self._state.with_changes(**changes)
            state = self._state
            listeners = tuple(self._listeners)
        for listener in listeners:
            listener(state)
        return state
