"""Zentrale Betriebszustandsmaschine für CarenDMR.

Sie ist die einzige fachliche Quelle dafür, ob Parameter editierbar sind und ob
PTT verwendet werden darf. GUI, Hotkeys und TX-Steuerung leiten ihre Freigaben
nur aus diesem Zustand ab.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from threading import RLock
from typing import Callable


class RadioState(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    TRANSMITTING = "transmitting"
    DISCONNECTING = "disconnecting"
    ERROR = "error"


_ALLOWED: dict[RadioState, set[RadioState]] = {
    RadioState.DISCONNECTED: {RadioState.CONNECTING, RadioState.ERROR},
    RadioState.CONNECTING: {RadioState.CONNECTED, RadioState.DISCONNECTED, RadioState.ERROR},
    RadioState.CONNECTED: {RadioState.TRANSMITTING, RadioState.DISCONNECTING, RadioState.ERROR},
    RadioState.TRANSMITTING: {RadioState.CONNECTED, RadioState.DISCONNECTING, RadioState.ERROR},
    RadioState.DISCONNECTING: {RadioState.DISCONNECTED, RadioState.ERROR},
    RadioState.ERROR: {RadioState.DISCONNECTED, RadioState.CONNECTING},
}


@dataclass(frozen=True, slots=True)
class RadioStateSnapshot:
    state: RadioState

    @property
    def can_transmit(self) -> bool:
        return self.state is RadioState.CONNECTED

    @property
    def can_edit_parameters(self) -> bool:
        return self.state in {RadioState.DISCONNECTED, RadioState.ERROR}

    @property
    def is_connected(self) -> bool:
        return self.state in {RadioState.CONNECTED, RadioState.TRANSMITTING}

    @property
    def is_busy(self) -> bool:
        return self.state in {
            RadioState.CONNECTING,
            RadioState.TRANSMITTING,
            RadioState.DISCONNECTING,
        }


class RadioStateMachine:
    def __init__(self, initial: RadioState = RadioState.DISCONNECTED) -> None:
        self._state = initial
        self._lock = RLock()
        self._listeners: list[Callable[[RadioStateSnapshot], None]] = []

    @property
    def state(self) -> RadioState:
        with self._lock:
            return self._state

    def snapshot(self) -> RadioStateSnapshot:
        return RadioStateSnapshot(self.state)

    def subscribe(self, listener: Callable[[RadioStateSnapshot], None]) -> None:
        with self._lock:
            self._listeners.append(listener)

    def transition(self, target: RadioState, *, force: bool = False) -> RadioStateSnapshot:
        target = RadioState(target)
        with self._lock:
            current = self._state
            if target is current:
                return RadioStateSnapshot(current)
            if not force and target not in _ALLOWED[current]:
                raise RuntimeError(f"Ungültiger Betriebszustandswechsel: {current.value} -> {target.value}")
            self._state = target
            snapshot = RadioStateSnapshot(target)
            listeners = tuple(self._listeners)
        for listener in listeners:
            listener(snapshot)
        return snapshot

    def synchronize(self, target: RadioState) -> RadioStateSnapshot:
        """Übernimmt einen belegten technischen Zustand ohne Übergangsprüfung.

        Das wird nur verwendet, wenn der ReceiveService seinen realen Zustand
        meldet. Dadurch kann sich die GUI nach Fehlern oder Thread-Enden wieder
        an die technische Wahrheit angleichen.
        """
        return self.transition(target, force=True)
