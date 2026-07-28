"""Ausgabeschnittstelle für spätere Sprachausgabe."""

from __future__ import annotations

from typing import Protocol

from carendmr.core.events import EventBus
from carendmr.core.status import StatusChangedEvent

from .messages import message_for_status


class SpeechOutput(Protocol):
    """Abstrakte Ausgabe, später z. B. Windows SAPI oder macOS Speech."""

    def speak(self, text: str) -> None:
        """Gibt einen Text hörbar oder ersatzweise sichtbar aus."""


class ConsoleSpeechOutput:
    """Erste vollständig testbare Ausgabe ohne zusätzliche Abhängigkeiten."""

    def speak(self, text: str) -> None:
        print(text)


class SpeechManager:
    """Reagiert auf Statusänderungen und erzeugt verständliche Meldungen."""

    def __init__(self, event_bus: EventBus, output: SpeechOutput) -> None:
        self._event_bus = event_bus
        self._output = output
        self._started = False

    def start(self) -> None:
        """Aktiviert die Reaktion auf Statusänderungen."""
        if self._started:
            return
        self._event_bus.subscribe(StatusChangedEvent, self._on_status_changed)
        self._started = True

    def stop(self) -> None:
        """Deaktiviert die Reaktion auf Statusänderungen."""
        if not self._started:
            return
        self._event_bus.unsubscribe(StatusChangedEvent, self._on_status_changed)
        self._started = False

    def say(self, text: str) -> None:
        """Gibt eine direkte, bereits verständliche Meldung aus."""
        cleaned = text.strip()
        if cleaned:
            self._output.speak(cleaned)

    def _on_status_changed(self, event: StatusChangedEvent) -> None:
        self._output.speak(message_for_status(event.current, event.detail))
