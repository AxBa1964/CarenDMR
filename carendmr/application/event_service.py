"""Kompatible Fassade über dem zentralen Informationsmanager."""

from __future__ import annotations

from typing import Callable, Mapping

from carendmr.domain import ApplicationEvent, EventLevel
from carendmr.domain.information import (
    InformationCategory,
    InformationMessage,
    InformationPriority,
    OperatingContext,
)

from .information_manager import InformationDiagnostics, InformationManager


class EventService:
    """Bestehende Ereignis-API mit getrennten Ausgabekanälen."""

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

    def subscribe_log(self, listener: Callable[[InformationMessage], None]) -> None:
        self.information.subscribe_log(listener)

    def set_context(self, context: OperatingContext) -> None:
        self.information.set_context(context)

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
        context: OperatingContext | None = None,
        metadata: Mapping[str, object] | None = None,
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
            context=context,
            metadata=metadata,
        )
        return ApplicationEvent.from_information(information)

    def snapshot(self) -> tuple[ApplicationEvent, ...]:
        return tuple(ApplicationEvent.from_information(item) for item in self.information.snapshot())

    def diagnostics(self) -> InformationDiagnostics:
        return self.information.diagnostics()
