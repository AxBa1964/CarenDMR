"""GUI- und hardwareunabhängige Bedien-Schnittstelle für den Funkbetrieb.

Diese Fassade ist der gemeinsame Einstiegspunkt für Qt, eine spätere
Raspberry-Pi-Hardwarebedienung und weitere Oberflächen. Sie enthält keine
Widget- oder GPIO-Abhängigkeiten.

Ab 0.2.1.85 bietet sie zusätzlich asynchrone Varianten (``connect_async``,
``disconnect_async``, ``start_ptt``/``stop_ptt``). Damit müssen Oberflächen
keine eigenen Hintergrund-Threads für den Funkablauf mehr starten.
Rückmeldungen (``on_done``/``on_error``) laufen im Hintergrund-Thread; eine
Oberfläche muss sie selbst in ihren GUI-Thread übergeben (z. B. per Queue).
"""
from __future__ import annotations

from threading import Event, Lock, Thread
from typing import Any, Callable

from carendmr.domain.models import ApplicationState, ConnectionState

from .connection_manager import ConnectionManager
from .radio_state_machine import RadioState, RadioStateMachine, RadioStateSnapshot
from .receive_service import ReceiveService

DoneCallback = Callable[[Any], None]
ErrorCallback = Callable[[Exception], None]


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
        self._lock = Lock()
        self._connect_in_flight = False
        self._ptt_stop_event: Event | None = None
        self.receive_service.state_store.subscribe(self._on_application_state)

    def subscribe(self, listener: Callable[[RadioStateSnapshot], None]) -> None:
        self.radio_state.subscribe(listener)

    def snapshot(self) -> RadioStateSnapshot:
        return self.radio_state.snapshot()

    @property
    def is_transmitting(self) -> bool:
        with self._lock:
            return self._ptt_stop_event is not None

    # ------------------------------------------------------------------
    # Synchrone Bedienung (blockiert den Aufrufer)
    # ------------------------------------------------------------------
    def connect(self, talkgroup: int, timeslot: int, call_type: str = "group") -> bool:
        self._begin_connect(talkgroup, timeslot, call_type)
        return self._perform_connect(talkgroup, timeslot, call_type)

    def disconnect(self, *, wait_timeout: float | None = None) -> bool:
        """Beendet die Funkverbindung über den zentralen ConnectionManager.

        Oberflächen dürfen optional auf das tatsächliche Ende des RX-Threads
        warten, ohne dafür direkt auf den ReceiveService zugreifen zu müssen.
        """
        self._begin_disconnect()
        return self._perform_disconnect(wait_timeout)

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
        self._begin_ptt(stop_event)
        return self._perform_ptt(
            stop_event,
            level_callback=level_callback,
            optimize=optimize,
            rx_playback_gate=rx_playback_gate,
            tx_complete_callback=tx_complete_callback,
        )

    # ------------------------------------------------------------------
    # Asynchrone Bedienung (kehrt sofort zurück)
    # ------------------------------------------------------------------
    def connect_async(
        self,
        talkgroup: int,
        timeslot: int,
        call_type: str = "group",
        *,
        on_done: DoneCallback | None = None,
        on_error: ErrorCallback | None = None,
    ) -> Thread:
        """Prüft das Ziel sofort und verbindet im Hintergrund.

        Ungültige Ziele lösen ``ValueError`` direkt beim Aufruf aus.
        ``on_done`` erhält das Ergebnis von ``ConnectionManager.connect``.
        """
        self._begin_connect(talkgroup, timeslot, call_type)
        return self._run_async(
            "CarenDMR-Connect",
            lambda: self._perform_connect(talkgroup, timeslot, call_type),
            on_done,
            on_error,
        )

    def disconnect_async(
        self,
        *,
        wait_timeout: float | None = 8.0,
        on_done: DoneCallback | None = None,
        on_error: ErrorCallback | None = None,
    ) -> Thread:
        """Beendet eine laufende Sendung und trennt im Hintergrund.

        ``on_done`` erhält ``True``, sobald der Empfang beendet ist (bzw. ob
        er innerhalb von ``wait_timeout`` Sekunden endete).
        """
        self._begin_disconnect()
        return self._run_async(
            "CarenDMR-Disconnect",
            lambda: self._perform_disconnect(wait_timeout),
            on_done,
            on_error,
        )

    def start_ptt(
        self,
        *,
        level_callback: Callable[[float], None] | None = None,
        optimize: bool = True,
        rx_playback_gate: Event | None = None,
        tx_complete_callback: Callable[[], None] | None = None,
        on_done: DoneCallback | None = None,
        on_error: ErrorCallback | None = None,
    ) -> Event:
        """Startet TX im Hintergrund und gibt das Stop-Ereignis zurück.

        Ohne aktive Verbindung oder bei bereits laufender Sendung wird
        ``RuntimeError`` sofort ausgelöst. ``stop_ptt()`` beendet die Sendung.
        """
        stop_event = Event()
        self._begin_ptt(stop_event)
        self._run_async(
            "CarenDMR-PTT",
            lambda: self._perform_ptt(
                stop_event,
                level_callback=level_callback,
                optimize=optimize,
                rx_playback_gate=rx_playback_gate,
                tx_complete_callback=tx_complete_callback,
            ),
            on_done,
            on_error,
        )
        return stop_event

    def stop_ptt(self) -> bool:
        """Fordert das Ende der laufenden Sendung an. ``False``, wenn keine läuft."""
        with self._lock:
            stop_event = self._ptt_stop_event
        if stop_event is None:
            return False
        stop_event.set()
        return True

    # ------------------------------------------------------------------
    # Interne Abläufe
    # ------------------------------------------------------------------
    def _begin_connect(self, talkgroup: int, timeslot: int, call_type: str) -> None:
        self._validate_target(talkgroup, timeslot, call_type)
        self.radio_state.transition(RadioState.CONNECTING)
        with self._lock:
            self._connect_in_flight = True

    def _perform_connect(self, talkgroup: int, timeslot: int, call_type: str) -> bool:
        try:
            started = self.connection_manager.connect(talkgroup, timeslot, call_type)
            if not started and not self.receive_service.is_running:
                raise RuntimeError("Der Empfangsdienst konnte nicht gestartet werden.")
        except Exception:
            with self._lock:
                self._connect_in_flight = False
            self.radio_state.synchronize(RadioState.ERROR)
            raise
        with self._lock:
            self._connect_in_flight = False
        # Bei unverändertem Ziel startet der ConnectionManager nichts neu; dann
        # meldet der StateStore auch keinen neuen Zustand mehr.
        if not started and self.receive_service.is_running:
            self.radio_state.synchronize(RadioState.CONNECTED)
        return started

    def _begin_disconnect(self) -> None:
        self.stop_ptt()
        if self.radio_state.snapshot().is_connected:
            self.radio_state.transition(RadioState.DISCONNECTING)

    def _perform_disconnect(self, wait_timeout: float | None) -> bool:
        self.connection_manager.disconnect()
        if wait_timeout is None:
            return True
        return bool(self.receive_service.wait(float(wait_timeout)))

    def _begin_ptt(self, stop_event: Event) -> None:
        if not self.radio_state.snapshot().can_transmit:
            raise RuntimeError("PTT ist nur bei aktiver Verbindung möglich.")
        with self._lock:
            if self._ptt_stop_event is not None:
                raise RuntimeError("Es läuft bereits eine Sendung.")
            self._ptt_stop_event = stop_event
        self.radio_state.transition(RadioState.TRANSMITTING)

    def _perform_ptt(
        self,
        stop_event: Event,
        *,
        level_callback: Callable[[float], None] | None,
        optimize: bool,
        rx_playback_gate: Event | None,
        tx_complete_callback: Callable[[], None] | None,
    ):
        try:
            return self.connection_manager.run_parrot_hold_to_talk(
                stop_event,
                level_callback=level_callback,
                optimize=optimize,
                rx_playback_gate=rx_playback_gate,
                tx_complete_callback=tx_complete_callback,
            )
        finally:
            with self._lock:
                if self._ptt_stop_event is stop_event:
                    self._ptt_stop_event = None
            # Wurde während der Sendung bereits getrennt, bleibt DISCONNECTING
            # stehen; der StateStore meldet anschließend DISCONNECTED.
            if self.radio_state.state is not RadioState.DISCONNECTING:
                self.radio_state.synchronize(
                    RadioState.CONNECTED if self.receive_service.is_running else RadioState.DISCONNECTED
                )

    @staticmethod
    def _run_async(
        name: str,
        operation: Callable[[], Any],
        on_done: DoneCallback | None,
        on_error: ErrorCallback | None,
    ) -> Thread:
        def worker() -> None:
            try:
                result = operation()
            except Exception as error:
                if on_error is not None:
                    on_error(error)
                return
            if on_done is not None:
                on_done(result)

        thread = Thread(target=worker, name=name, daemon=True)
        thread.start()
        return thread

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
        # Beim Zielwechsel stoppt ConnectionManager.connect() zuerst die alte
        # Sitzung; deren STOPPING/DISCONNECTED ist kein Bedienzustand. Gefiltert
        # wird nur, solange connect() selbst läuft. Endet der neue Empfang danach
        # ohne Verbindung, wird DISCONNECTED weiterhin übernommen.
        if target in {RadioState.DISCONNECTING, RadioState.DISCONNECTED}:
            with self._lock:
                connecting = self._connect_in_flight
            if connecting:
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
