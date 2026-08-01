"""Zentrale, technisch neutrale Zustandsverwaltung."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .events import Event, EventBus


class AppStatus(str, Enum):
    """Zustände, die alle späteren Komponenten gemeinsam verstehen."""

    STARTING = "starting"
    READY = "ready"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECEIVING = "receiving"
    TRANSMITTING = "transmitting"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class StatusChangedEvent(Event):
    """Wird veröffentlicht, wenn sich der Anwendungszustand ändert."""

    previous: AppStatus = AppStatus.STARTING
    current: AppStatus = AppStatus.STARTING
    detail: str | None = None


class StatusManager:
    """Speichert den aktuellen Zustand und meldet echte Änderungen."""

    def __init__(
        self,
        event_bus: EventBus,
        initial_status: AppStatus = AppStatus.STARTING,
    ) -> None:
        self._event_bus = event_bus
        self._status = initial_status
        self._detail: str | None = None

    @property
    def status(self) -> AppStatus:
        """Aktueller Zustand."""
        return self._status

    @property
    def detail(self) -> str | None:
        """Optionale, menschenlesbare Zusatzinformation."""
        return self._detail

    def set_status(
        self,
        status: AppStatus,
        detail: str | None = None,
        *,
        force: bool = False,
    ) -> bool:
        """Setzt den Zustand und veröffentlicht bei Änderung ein Ereignis.

        Rückgabewert:
            True, wenn ein Ereignis veröffentlicht wurde.
            False, wenn Zustand und Detail unverändert waren.
        """
        if not force and status == self._status and detail == self._detail:
            return False

        previous = self._status
        self._status = status
        self._detail = detail
        self._event_bus.publish(
            StatusChangedEvent(
                previous=previous,
                current=status,
                detail=detail,
            )
        )
        return True
