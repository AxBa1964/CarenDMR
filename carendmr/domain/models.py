"""UI-unabhängige Fachmodelle für den CarenDMR-Betriebszustand."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from .current_call import CurrentCall


class ConnectionState(str, Enum):
    DISCONNECTED = "Getrennt"
    CONNECTING = "Verbindung wird hergestellt"
    CONNECTED = "Verbunden"
    RECEIVING = "Empfang aktiv"
    STOPPING = "Empfang wird beendet"
    ERROR = "Fehler"


@dataclass(frozen=True, slots=True)
class ReceiveStatistics:
    elapsed_seconds: float = 0.0
    datagrams: int = 0
    voice_bursts: int = 0
    decoded_codewords: int = 0
    decode_errors: int = 0
    corrected_errors: int = 0
    concealed_bursts: int = 0
    invalid_dmrd: int = 0


@dataclass(frozen=True, slots=True)
class ApplicationState:
    connection: ConnectionState = ConnectionState.DISCONNECTED
    server: str = "Nicht verbunden"
    talkgroup: int = 91
    timeslot: int = 2
    brandmeister_connected: bool = False
    receive_active: bool = False
    audio_active: bool = False
    message: str = "Bereit"
    statistics: ReceiveStatistics = ReceiveStatistics()
    current_call: CurrentCall | None = None

    def with_changes(self, **changes: object) -> "ApplicationState":
        return replace(self, **changes)
