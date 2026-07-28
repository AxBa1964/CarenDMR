"""Kleiner synchroner EventBus für voneinander getrennte Komponenten."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, DefaultDict, TypeVar
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class Event:
    """Basisklasse für Ereignisse innerhalb von CarenDMR."""

    event_id: str = field(default_factory=lambda: uuid4().hex)
    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


EventType = TypeVar("EventType", bound=Event)
EventHandler = Callable[[Event], None]


class EventBus:
    """Verteilt Ereignisse synchron an registrierte Empfänger.

    Die synchrone Ausführung ist für den aktuellen Projektstand bewusst
    gewählt: Sie ist leicht nachvollziehbar und vollständig testbar.
    Hintergrund-Threads werden erst eingeführt, wenn Audio oder Netzwerk
    dies tatsächlich erfordern.
    """

    def __init__(self) -> None:
        self._subscribers: DefaultDict[type[Event], list[EventHandler]] = (
            defaultdict(list)
        )

    def subscribe(
        self,
        event_type: type[EventType],
        handler: Callable[[EventType], None],
    ) -> None:
        """Registriert einen Handler genau einmal."""
        handlers = self._subscribers[event_type]
        if handler not in handlers:
            handlers.append(handler)  # type: ignore[arg-type]

    def unsubscribe(
        self,
        event_type: type[EventType],
        handler: Callable[[EventType], None],
    ) -> None:
        """Entfernt einen Handler. Ein fehlender Handler ist kein Fehler."""
        handlers = self._subscribers.get(event_type)
        if not handlers:
            return
        try:
            handlers.remove(handler)  # type: ignore[arg-type]
        except ValueError:
            return

    def publish(self, event: Event) -> None:
        """Veröffentlicht ein Ereignis an passend registrierte Handler."""
        for registered_type, handlers in tuple(self._subscribers.items()):
            if isinstance(event, registered_type):
                for handler in tuple(handlers):
                    handler(event)

    def clear(self) -> None:
        """Entfernt alle Registrierungen; hauptsächlich für Tests."""
        self._subscribers.clear()
