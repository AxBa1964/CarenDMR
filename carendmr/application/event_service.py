"""Kompatible Fassade über dem zentralen Informationsmanager."""

from __future__ import annotations

from typing import Callable

from carendmr.domain import ApplicationEvent, EventLevel
from carendmr.domain.information import (
    InformationCategory,
    InformationMessage,
    InformationPriority,
)

from .information_manager import InformationManager


class EventService:
    """Bestehende Ereignis-API mit zwei getrennten Ausgabekanälen.

    ``subscribe`` bleibt der visuelle Kanal für die vorhandene GUI. Neue
    sprachliche Ausgaben werden über ``subscribe_speech`` angebunden.
    """

    def __init__(self, *, maximum: int = 500) -> None:
        self.information = InformationManager(maximum=maximum)

    def subscribe(self, listener: Callable[[ApplicationEvent], None]) -> None:
        def adapter(message: InformationMessage) -> None:
            listener(ApplicationEvent.from_information(message))
        self.information.subscribe_visual(adapter)

    def subscribe_information(self, listener: Callable[[InformationMessage], None]) -> None:
        self.information.subscribe_visual(listener)

    def subscribe_speech(self, listener: Callable[[InformationMessage], None]) -> None:
        self.information.subscribe_speech(listener)

    def publish(
        self,
        message: str,
        level: EventLevel = EventLevel.INFO,
        *,
        code: str = "general.message",
        long_text: str | None = None,
        category: InformationCategory = InformationCategory.SYSTEM,
        priority: InformationPriority = InformationPriority.NORMAL,
        action_hint: str | None = None,
        speak: bool = True,
    ) -> ApplicationEvent:
        information = self.information.publish(
            message,
            code=code,
            long_text=long_text,
            category=category,
            priority=priority,
            level=level,
            action_hint=action_hint,
            speak=speak,
        )
        return ApplicationEvent.from_information(information)

    def snapshot(self) -> tuple[ApplicationEvent, ...]:
        return tuple(ApplicationEvent.from_information(item) for item in self.information.snapshot())
