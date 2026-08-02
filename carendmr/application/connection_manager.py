"""Zentrale Steuerung für Empfang, TG-/TS-Wechsel und TX-Rückkehr."""

from __future__ import annotations

from threading import Event, Lock
from typing import Callable

from carendmr.domain import EventLevel

from .event_service import EventService
from .parrot_test_service import ParrotTestService
from .receive_service import ReceiveService


class ConnectionManager:
    """Koordiniert alle Zustandswechsel zwischen RX und dem Parrot-Sendepfad.

    Der Empfangsdienst bleibt Eigentümer der BrandMeister-Empfangsverbindung.
    Der Parrot-Test verwendet weiterhin seine eigene, kurzlebige Verbindung. Nach
    jedem TX-Versuch wird ein zuvor aktiver Empfang automatisch wiederhergestellt.
    """

    def __init__(
        self,
        receive_service: ReceiveService,
        parrot_service: ParrotTestService,
        *,
        events: EventService | None = None,
        receive_stop_timeout: float = 8.0,
    ) -> None:
        self.receive_service = receive_service
        self.parrot_service = parrot_service
        self.events = events or receive_service.events
        self.receive_stop_timeout = float(receive_stop_timeout)
        self._operation_lock = Lock()

    @property
    def is_busy(self) -> bool:
        return self._operation_lock.locked() or self.receive_service.is_switching

    def connect(self, talkgroup: int, timeslot: int, call_type: str = "group") -> bool:
        with self._operation_lock:
            self.receive_service.set_receive_target(talkgroup, timeslot, call_type)
            return self.receive_service.start()

    def disconnect(self) -> None:
        with self._operation_lock:
            self.receive_service.stop()

    def switch_receive_target(self, talkgroup: int, timeslot: int, call_type: str = "group") -> bool:
        if self._operation_lock.locked():
            return False
        try:
            return self.receive_service.switch_receive_target(talkgroup, timeslot, call_type)
        except TypeError:
            # Rückwärtskompatibilität für Test-/Mock-Dienste ohne Rufart-Parameter.
            return self.receive_service.switch_receive_target(talkgroup, timeslot)

    def run_parrot_hold_to_talk(
        self,
        stop_event: Event,
        *,
        level_callback: Callable[[float], None] | None = None,
        optimize: bool = True,
    ):
        """Führt TX aus und stellt einen vorher aktiven Empfang stets wieder her."""
        with self._operation_lock:
            resume_receive = self.receive_service.is_running
            talkgroup = self.receive_service.target_talkgroup
            timeslot = self.receive_service.target_timeslot

            if resume_receive:
                self.events.publish(
                    "Empfang wird für den Parrot-Test kontrolliert angehalten."
                )
                self.receive_service.stop()
                if not self.receive_service.wait(self.receive_stop_timeout):
                    raise RuntimeError(
                        "Der Empfang konnte für den Parrot-Test nicht rechtzeitig beendet werden."
                    )

            try:
                return self.parrot_service.run_hold_to_talk(
                    stop_event,
                    level_callback=level_callback,
                    optimize=optimize,
                )
            finally:
                if resume_receive:
                    self.events.publish(
                        f"Empfang auf Talkgroup {talkgroup}, Timeslot {timeslot} wird automatisch wiederhergestellt."
                    )
                    try:
                        self.receive_service.set_receive_target(talkgroup, timeslot)
                        if not self.receive_service.start():
                            raise RuntimeError("Empfangsdienst wurde nicht gestartet.")
                    except Exception as error:
                        self.events.publish(
                            f"Automatische Rückkehr zum Empfang fehlgeschlagen: {error}",
                            EventLevel.ERROR,
                        )
