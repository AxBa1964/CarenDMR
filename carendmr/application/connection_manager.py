"""Zentrale Steuerung für Empfang, TG-/TS-Wechsel und TX-Rückkehr."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Event, Lock, Thread
from typing import Callable

from carendmr.diagnostics.tx_rx_timing import mark as timing_mark, start_cycle as timing_start_cycle

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
        """Stellt einen definierten Empfangszustand her.

        Ein noch laufender oder nur teilweise beendeter RX-Thread wird zuerst
        vollständig gestoppt. Dadurch können GUI- und RX-Zustand nach schnellen
        Seitenwechseln oder mehrfachen Connect-Aktionen nicht auseinanderlaufen.
        """
        with self._operation_lock:
            if self.receive_service.is_running:
                same_target = (
                    self.receive_service.target_talkgroup == int(talkgroup)
                    and self.receive_service.target_timeslot == int(timeslot)
                    and self.receive_service.target_call_type == str(call_type).strip().lower()
                )
                if same_target:
                    return False
                self.receive_service.stop()
                if not self.receive_service.wait(self.receive_stop_timeout):
                    raise RuntimeError("Der laufende Empfang konnte nicht rechtzeitig beendet werden.")
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

    def run_parrot_hold_to_talk(self, stop_event: Event, *, level_callback: Callable[[float], None] | None = None, optimize: bool = True, rx_playback_gate: Event | None = None):
        with self._operation_lock:
            resume_receive=self.receive_service.is_running
            talkgroup=self.receive_service.target_talkgroup; timeslot=self.receive_service.target_timeslot
            call_type=getattr(self.receive_service,"target_call_type","group")
            started_at=datetime.now(timezone.utc).isoformat()
            timing_start_cycle(f"PTT EIN TG={talkgroup} TS={timeslot} Rufart={call_type}")
            timing_mark("PTT_EIN","Live-Aufnahme und RX-Stopp beginnen")
            supports_live=hasattr(self.parrot_service,"start_live_hold_to_talk") and hasattr(self.parrot_service,"transmit_live_capture")
            if not supports_live:
                if resume_receive:
                    self.receive_service.stop()
                    if not self.receive_service.wait(self.receive_stop_timeout):
                        raise RuntimeError("Der Empfang konnte für den Sendebetrieb nicht rechtzeitig beendet werden.")
                try:
                    return self.parrot_service.run_hold_to_talk(
                        stop_event, level_callback=level_callback, optimize=optimize
                    )
                finally:
                    if resume_receive:
                        try:
                            self.receive_service.set_receive_target(talkgroup, timeslot)
                            self.receive_service.start()
                        except Exception as error:
                            self.events.publish(
                                f"Automatische Rückkehr zum Empfang fehlgeschlagen: {error}",
                                EventLevel.ERROR,
                            )
            capture=self.parrot_service.start_live_hold_to_talk(stop_event,level_callback=level_callback)
            timing_mark("MIKROFON_START_ANGEFORDERT")
            if resume_receive:
                self.receive_service.stop(); timing_mark("RX_STOP_ANGEFORDERT")
                if not self.receive_service.wait(self.receive_stop_timeout):
                    stop_event.set(); raise RuntimeError("Der Empfang konnte für den Sendebetrieb nicht rechtzeitig beendet werden.")
                timing_mark("RX_BEENDET")
            try:
                timing_mark("TX_LIVE_VERARBEITUNG_START")
                return self.parrot_service.transmit_live_capture(capture,optimize=optimize,started_at=started_at,destination_id=talkgroup,timeslot=timeslot,call_type=call_type,rx_playback_gate=rx_playback_gate)
            finally:
                if resume_receive:
                    try:
                        self.receive_service.set_receive_target(talkgroup,timeslot,call_type); timing_mark("RX_NEUSTART_ANGEFORDERT")
                        if not self.receive_service.start(): raise RuntimeError("Empfangsdienst wurde nicht gestartet.")
                        timing_mark("RX_THREAD_GESTARTET")
                    except Exception as error:
                        self.events.publish(f"Automatische Rückkehr zum Empfang fehlgeschlagen: {error}",EventLevel.ERROR)
