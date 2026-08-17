"""Zentraler Verteiler für visuelle und sprachliche Betriebsinformationen."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from time import perf_counter_ns
from typing import Callable, Mapping

from carendmr.domain import EventLevel
from carendmr.domain.information import (
    InformationCategory,
    InformationMessage,
    InformationPriority,
    OperatingContext,
)


@dataclass(frozen=True, slots=True)
class DispatchMeasurement:
    """Leichtgewichtige Laufzeitmessung eines einzelnen Informationsereignisses."""

    code: str
    timestamp: datetime
    total_ms: float
    visual_ms: float
    speech_ms: float
    log_ms: float
    queue_depth: int


@dataclass(frozen=True, slots=True)
class InformationDiagnostics:
    events_total: int
    average_ms: float
    maximum_ms: float
    visual_average_ms: float
    speech_average_ms: float
    log_average_ms: float
    queue_current: int
    queue_maximum: int
    warning_count: int
    slow_count: int
    critical_count: int


class InformationManager:
    """Verteilt dieselbe fachliche Information an getrennte Ausgabekanäle.

    Die Komponente bleibt synchron und absichtlich sehr leichtgewichtig. Ihre
    Laufzeitmessung macht dennoch früh sichtbar, wenn GUI, spätere TTS oder
    Logging den Funkbetrieb beeinträchtigen könnten.
    """

    WARNING_MS = 5.0
    SLOW_MS = 20.0
    CRITICAL_MS = 50.0

    def __init__(self, *, maximum: int = 500, diagnostic_maximum: int = 512) -> None:
        if maximum < 1:
            raise ValueError("Der Informationsmanager benötigt mindestens einen Eintrag.")
        if diagnostic_maximum < 1:
            raise ValueError("Der Diagnose-Ringpuffer benötigt mindestens einen Eintrag.")
        self._messages: deque[InformationMessage] = deque(maxlen=maximum)
        self._measurements: deque[DispatchMeasurement] = deque(maxlen=diagnostic_maximum)
        self._visual_listeners: list[Callable[[InformationMessage], None]] = []
        self._speech_listeners: list[Callable[[InformationMessage], None]] = []
        self._log_listeners: list[Callable[[InformationMessage], None]] = []
        self._lock = Lock()
        self._context = OperatingContext.UNKNOWN
        self._events_total = 0
        self._total_ns = 0
        self._maximum_ns = 0
        self._visual_ns = 0
        self._speech_ns = 0
        self._log_ns = 0
        self._queue_current = 0
        self._queue_maximum = 0
        self._warning_count = 0
        self._slow_count = 0
        self._critical_count = 0

    @property
    def context(self) -> OperatingContext:
        with self._lock:
            return self._context

    def set_context(self, context: OperatingContext) -> None:
        if not isinstance(context, OperatingContext):
            raise TypeError("context muss ein OperatingContext sein.")
        with self._lock:
            self._context = context

    def subscribe_visual(self, listener: Callable[[InformationMessage], None]) -> None:
        with self._lock:
            self._visual_listeners.append(listener)

    def subscribe_speech(self, listener: Callable[[InformationMessage], None]) -> None:
        with self._lock:
            self._speech_listeners.append(listener)

    def subscribe_log(self, listener: Callable[[InformationMessage], None]) -> None:
        with self._lock:
            self._log_listeners.append(listener)

    @staticmethod
    def _dispatch(listeners: tuple[Callable[[InformationMessage], None], ...], message: InformationMessage) -> int:
        started = perf_counter_ns()
        for listener in listeners:
            listener(message)
        return perf_counter_ns() - started

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
        context: OperatingContext | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> InformationMessage:
        dispatch_started = perf_counter_ns()
        cleaned = short_text.strip()
        if not cleaned:
            raise ValueError("Eine Information benötigt einen Text.")
        with self._lock:
            current_context = context or self._context
            self._queue_current += 1
            self._queue_maximum = max(self._queue_maximum, self._queue_current)
        message = InformationMessage(
            timestamp=datetime.now(),
            code=code.strip() or "general.message",
            short_text=cleaned,
            long_text=(long_text or cleaned).strip(),
            category=category,
            priority=priority,
            level=level,
            action_hint=action_hint.strip() if action_hint else None,
            speak=bool(speak),
            context=current_context,
            metadata=dict(metadata) if metadata else None,
        )
        with self._lock:
            self._messages.append(message)
            visual = tuple(self._visual_listeners)
            speech = tuple(self._speech_listeners)
            log = tuple(self._log_listeners)
            queue_depth = self._queue_current

        visual_ns = speech_ns = log_ns = 0
        try:
            visual_ns = self._dispatch(visual, message)
            if message.speak:
                speech_ns = self._dispatch(speech, message)
            log_ns = self._dispatch(log, message)
            return message
        finally:
            total_ns = perf_counter_ns() - dispatch_started
            total_ms = total_ns / 1_000_000.0
            measurement = DispatchMeasurement(
                code=message.code,
                timestamp=message.timestamp,
                total_ms=total_ms,
                visual_ms=visual_ns / 1_000_000.0,
                speech_ms=speech_ns / 1_000_000.0,
                log_ms=log_ns / 1_000_000.0,
                queue_depth=queue_depth,
            )
            with self._lock:
                self._measurements.append(measurement)
                self._events_total += 1
                self._total_ns += total_ns
                self._maximum_ns = max(self._maximum_ns, total_ns)
                self._visual_ns += visual_ns
                self._speech_ns += speech_ns
                self._log_ns += log_ns
                if total_ms > self.WARNING_MS:
                    self._warning_count += 1
                if total_ms > self.SLOW_MS:
                    self._slow_count += 1
                if total_ms > self.CRITICAL_MS:
                    self._critical_count += 1
                self._queue_current = max(0, self._queue_current - 1)

    def snapshot(self) -> tuple[InformationMessage, ...]:
        with self._lock:
            return tuple(self._messages)

    def recent(self, count: int = 10) -> tuple[InformationMessage, ...]:
        if count < 1:
            return ()
        with self._lock:
            return tuple(self._messages)[-count:]

    def last(self, *, spoken_only: bool = False) -> InformationMessage | None:
        with self._lock:
            items = tuple(self._messages)
        for item in reversed(items):
            if not spoken_only or item.speak:
                return item
        return None

    def diagnostic_measurements(self) -> tuple[DispatchMeasurement, ...]:
        with self._lock:
            return tuple(self._measurements)

    def diagnostics(self) -> InformationDiagnostics:
        with self._lock:
            total = self._events_total
            divisor = total or 1
            return InformationDiagnostics(
                events_total=total,
                average_ms=(self._total_ns / divisor) / 1_000_000.0,
                maximum_ms=self._maximum_ns / 1_000_000.0,
                visual_average_ms=(self._visual_ns / divisor) / 1_000_000.0,
                speech_average_ms=(self._speech_ns / divisor) / 1_000_000.0,
                log_average_ms=(self._log_ns / divisor) / 1_000_000.0,
                queue_current=self._queue_current,
                queue_maximum=self._queue_maximum,
                warning_count=self._warning_count,
                slow_count=self._slow_count,
                critical_count=self._critical_count,
            )
