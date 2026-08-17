"""GUI- und hardwareunabhängige Bedien-Schnittstelle für den Funkbetrieb.

Diese Fassade ist der gemeinsame Einstiegspunkt für Qt, eine spätere
Raspberry-Pi-Hardwarebedienung und weitere Oberflächen. Sie enthält keine
Widget- oder GPIO-Abhängigkeiten.
"""
from __future__ import annotations

from threading import Event
from typing import Callable

from carendmr.domain.models import ApplicationState, ConnectionState

from .connection_manager import ConnectionManager
from .radio_state_machine import RadioState, RadioStateMachine, RadioStateSnapshot
from .receive_service import ReceiveService


class OperatingController:
    """Übersetzt Bedienbefehle in die vorhandene CarenDMR-Fachlogik."""

    def __init__(
        self,
        connection_manager: ConnectionManager,
        receive_service: ReceiveService,
        radio_state: RadioStateMachine | None = None,
    ) -> None:
        self.connection_manager = connection_manager
        self.receive_service = receive_service
        self.radio_state = radio_state or RadioStateMachine()
        self.receive_service.state_store.subscribe(self._on_application_state)

    def subscribe(self, listener: Callable[[RadioStateSnapshot], None]) -> None:
        self.radio_state.subscribe(listener)

    def snapshot(self) -> RadioStateSnapshot:
        return self.radio_state.snapshot()

    def connect(self, talkgroup: int, timeslot: int, call_type: str = "group") -> bool:
        self._validate_target(talkgroup, timeslot, call_type)
        self.radio_state.transition(RadioState.CONNECTING)
        try:
            started = self.connection_manager.connect(talkgroup, timeslot, call_type)
            if not started and not self.receive_service.is_running:
                raise RuntimeError("Der Empfangsdienst konnte nicht gestartet werden.")
            return started
        except Exception:
            self.radio_state.synchronize(RadioState.ERROR)
            raise

    def disconnect(self, *, wait_timeout: float | None = None) -> bool:
        """Beendet die Funkverbindung über den zentralen ConnectionManager.

        Oberflächen dürfen optional auf das tatsächliche Ende des RX-Threads
        warten, ohne dafür direkt auf den ReceiveService zugreifen zu müssen.
        """
        if self.radio_state.snapshot().is_connected:
            self.radio_state.transition(RadioState.DISCONNECTING)
        self.connection_manager.disconnect()
        if wait_timeout is None:
            return True
        return bool(self.receive_service.wait(float(wait_timeout)))

    def ptt(
        self,
        stop_event: Event,
        *,
        level_callback: Callable[[float], None] | None = None,
        optimize: bool = True,
        rx_playback_gate: Event | None = None,
        tx_complete_callback: Callable[[], None] | None = None,
    ):
        """Startet den vorhandenen TX-Pfad ohne UI-spezifische Funklogik.

        Die optionalen Callbacks werden lediglich an den bereits stabilen
        ConnectionManager weitergereicht. Dadurch können unterschiedliche
        Oberflächen denselben RX→TX→RX-Pfad verwenden.
        """
        if not self.radio_state.snapshot().can_transmit:
            raise RuntimeError("PTT ist nur bei aktiver Verbindung möglich.")
        self.radio_state.transition(RadioState.TRANSMITTING)
        try:
            return self.connection_manager.run_parrot_hold_to_talk(
                stop_event,
                level_callback=level_callback,
                optimize=optimize,
                rx_playback_gate=rx_playback_gate,
                tx_complete_callback=tx_complete_callback,
            )
        finally:
            self.radio_state.synchronize(
                RadioState.CONNECTED if self.receive_service.is_running else RadioState.DISCONNECTED
            )

    def _on_application_state(self, state: ApplicationState) -> None:
        mapping = {
            ConnectionState.CONNECTING: RadioState.CONNECTING,
            ConnectionState.CONNECTED: RadioState.CONNECTED,
            ConnectionState.RECEIVING: RadioState.CONNECTED,
            ConnectionState.STOPPING: RadioState.DISCONNECTING,
            ConnectionState.DISCONNECTED: RadioState.DISCONNECTED,
            ConnectionState.ERROR: RadioState.ERROR,
        }
        target = mapping[state.connection]
        # Während PTT wird der ReceiveService absichtlich für TX pausiert. Dabei
        # durchläuft sein ApplicationState STOPPING/DISCONNECTED, obwohl die
        # BrandMeister-Sitzung bestehen bleibt. Diese internen RX-Zustände dürfen
        # den Bedienzustand TRANSMITTING nicht überschreiben, sonst würde eine UI
        # den PTT-Knopf mitten in der Aussendung deaktivieren und PTT-AUS käme
        # nicht mehr beim stop_event an.
        if self.radio_state.state is RadioState.TRANSMITTING and target is not RadioState.ERROR:
            return
        self.radio_state.synchronize(target)

    @staticmethod
    def _validate_target(talkgroup: int, timeslot: int, call_type: str) -> None:
        if int(talkgroup) <= 0:
            raise ValueError("Talkgroup oder DMR-ID muss positiv sein.")
        if int(timeslot) not in (1, 2):
            raise ValueError("Timeslot muss 1 oder 2 sein.")
        if str(call_type).strip().lower() not in {"group", "private"}:
            raise ValueError("Rufart muss group oder private sein.")
