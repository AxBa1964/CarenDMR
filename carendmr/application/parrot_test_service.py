"""Anwendungsschicht für fest verriegelte private Parrot-Sprachtests."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from threading import Event
from typing import Callable

from carendmr.brandmeister.config import BrandMeisterConfigStore
from carendmr.brandmeister.parrot_voice import ParrotVoiceResult, execute_locked_parrot_voice_once
from carendmr.brandmeister.voice_transmit import execute_voice_once
from carendmr.brandmeister.live_voice_transmit import execute_live_voice_once
from carendmr.brandmeister.dmrd import DmrdCallType
from carendmr.domain import TransmitHistoryEntry
from carendmr.encoder import DroidStarPluginEncoder

from .transmit_history_service import TransmitHistoryService


TX_LEAD_IN_SECONDS = 0.240


class ParrotTestService:
    def __init__(self, project_root: Path, *, audio_service, encoder_service) -> None:
        self.project_root = Path(project_root)
        self.audio_service = audio_service
        self.encoder_service = encoder_service
        self.history = TransmitHistoryService(self.project_root)


    def start_live_hold_to_talk(self, stop_event: Event, *, level_callback: Callable[[float], None] | None = None):
        return self.audio_service.start_live_capture(stop_event, max_duration_seconds=float(self.audio_service.tx_safety_limit_seconds), level_callback=level_callback)

    def transmit_live_capture(self, capture, *, started_at: str, destination_id: int, timeslot: int, call_type: str, optimize: bool = True, rx_playback_gate: Event | None = None):
        plugin_path=self.encoder_service.configured_plugin_path
        if plugin_path is None: raise RuntimeError("Kein geprüftes DroidStar-Vocoder-Plugin konfiguriert.")
        self.encoder_service.verify_configured()
        config=BrandMeisterConfigStore(self.project_root / "config" / "brandmeister.local.json").load()
        is_parrot=destination_id==9990 and timeslot==2 and call_type=="private"
        with DroidStarPluginEncoder(self.project_root, plugin_path) as encoder:
            result=execute_live_voice_once(config,destination_id=destination_id,timeslot=timeslot,call_type=DmrdCallType.PRIVATE if call_type=="private" else DmrdCallType.GROUP,pcm_chunks=capture.chunks(),encoder=encoder,wait_for_parrot_echo=is_parrot,lead_in_seconds=TX_LEAD_IN_SECONDS,rx_debug_dir=(self.project_root / "logs" / "audio_debug") if self.audio_service.audio_debug_wav_enabled else None,rx_playback_gate=rx_playback_gate)
        duration=capture.duration_seconds
        if duration < 0.20: raise RuntimeError("Die TX-Taste wurde zu kurz gedrückt; es wurde nichts gesendet.")
        self.history.add(TransmitHistoryEntry(started_at=started_at,duration_seconds=duration,destination_id=destination_id,timeslot=timeslot,call_type="Privatruf" if call_type=="private" else "Gruppenruf",echo_received=result.echo_received,safety_limit_reached=capture.safety_limit_reached,optimizer_enabled=optimize))
        return result,duration,capture.safety_limit_reached

    def capture_hold_to_talk(
        self,
        stop_event: Event,
        *,
        level_callback: Callable[[float], None] | None = None,
        optimize: bool = True,
    ):
        """Startet die Mikrofonaufnahme ohne vorher auf das Ende von RX zu warten."""
        return self.audio_service.capture_transmit_pcm_until(
            stop_event,
            max_duration_seconds=float(self.audio_service.tx_safety_limit_seconds),
            level_callback=level_callback,
            optimize=optimize,
        )

    def transmit_captured_pcm(
        self,
        capture_result,
        *,
        optimize: bool = True,
        started_at: str | None = None,
        destination_id: int = 9990,
        timeslot: int = 2,
        call_type: str = "private",
    ):
        plugin_path = self.encoder_service.configured_plugin_path
        if plugin_path is None:
            raise RuntimeError("Kein geprüftes DroidStar-Vocoder-Plugin konfiguriert.")
        self.encoder_service.verify_configured()
        pcm, duration, safety_limit_reached, _diagnostics = capture_result
        if duration < 0.20:
            raise RuntimeError("Die TX-Taste wurde zu kurz gedrückt; es wurde nichts gesendet.")

        # Der DMR-Stream bekommt bewusst 240 ms Vorlauf. Dadurch sind Header und
        # erster Sprachburst bereits auf dem Netz, bevor die erste Silbe folgt.
        lead_in_samples = int(8000 * TX_LEAD_IN_SECONDS)
        pcm_with_lead_in = (0,) * lead_in_samples + tuple(pcm)

        config = BrandMeisterConfigStore(
            self.project_root / "config" / "brandmeister.local.json"
        ).load()
        with DroidStarPluginEncoder(self.project_root, plugin_path) as encoder:
            if destination_id == 9990 and timeslot == 2 and call_type == "private":
                result = execute_locked_parrot_voice_once(
                    config, pcm_samples=pcm_with_lead_in, encoder=encoder
                )
            else:
                result = execute_voice_once(
                    config, destination_id=destination_id, timeslot=timeslot,
                    call_type=DmrdCallType.PRIVATE if call_type == "private" else DmrdCallType.GROUP,
                    pcm_samples=pcm_with_lead_in, encoder=encoder
                )
        self.history.add(TransmitHistoryEntry(
            started_at=started_at or datetime.now(timezone.utc).isoformat(),
            duration_seconds=duration,
            destination_id=destination_id,
            timeslot=timeslot,
            call_type="Privatruf" if call_type == "private" else "Gruppenruf",
            echo_received=result.echo_received,
            safety_limit_reached=safety_limit_reached,
            optimizer_enabled=optimize,
        ))
        return result, duration, safety_limit_reached

    def run_hold_to_talk(
        self,
        stop_event: Event,
        *,
        level_callback: Callable[[float], None] | None = None,
        optimize: bool = True,
    ) -> tuple[ParrotVoiceResult, float, bool]:
        started_at = datetime.now(timezone.utc).isoformat()
        capture_result = self.capture_hold_to_talk(
            stop_event, level_callback=level_callback, optimize=optimize
        )
        return self.transmit_captured_pcm(
            capture_result, optimize=optimize, started_at=started_at
        )
