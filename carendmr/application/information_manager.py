"""Zentraler Verteiler für visuelle und sprachliche Betriebsinformationen."""

from __future__ import annotations

from collections import deque
from datetime import datetime
from threading import Lock
from typing import Callable

from carendmr.domain import EventLevel
from carendmr.domain.information import (
    InformationCategory,
    InformationMessage,
    InformationPriority,
)


class InformationManager:
    """Verteilt dieselbe fachliche Information an getrennte Ausgabekanäle."""

    def __init__(self, *, maximum: int = 500) -> None:
        if maximum < 1:
            raise ValueError("Der Informationsmanager benötigt mindestens einen Eintrag.")
        self._messages: deque[InformationMessage] = deque(maxlen=maximum)
        self._visual_listeners: list[Callable[[InformationMessage], None]] = []
        self._speech_listeners: list[Callable[[InformationMessage], None]] = []
        self._lock = Lock()

    def subscribe_visual(self, listener: Callable[[InformationMessage], None]) -> None:
        with self._lock:
            self._visual_listeners.append(listener)

    def subscribe_speech(self, listener: Callable[[InformationMessage], None]) -> None:
        with self._lock:
            self._speech_listeners.append(listener)

    def publish(
        self,
        short_text: str,
        *,
        code: str = "general.message",
        long_text: str | None = None,
        category: InformationCategory = InformationCategory.SYSTEM,
        priority: InformationPriority = InformationPriority.NORMAL,
        level: EventLevel = EventLevel.INFO,
        action_hint: str | None = None,
        speak: bool = True,
    ) -> InformationMessage:
        cleaned = short_text.strip()
        if not cleaned:
            raise ValueError("Eine Information benötigt einen Text.")
        message = InformationMessage(
            timestamp=datetime.now(),
            code=code,
            short_text=cleaned,
            long_text=(long_text or cleaned).strip(),
            category=category,
            priority=priority,
            level=level,
            action_hint=action_hint.strip() if action_hint else None,
            speak=bool(speak),
        )
        with self._lock:
            self._messages.append(message)
            visual = tuple(self._visual_listeners)
            speech = tuple(self._speech_listeners)
        for listener in visual:
            listener(message)
        if message.speak:
            for listener in speech:
                listener(message)
        return message

    def snapshot(self) -> tuple[InformationMessage, ...]:
        with self._lock:
            return tuple(self._messages)
