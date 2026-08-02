"""Anwendungsschicht für fest verriegelte private Parrot-Sprachtests."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from threading import Event
from typing import Callable

from carendmr.brandmeister.config import BrandMeisterConfigStore
from carendmr.brandmeister.parrot_voice import ParrotVoiceResult, execute_locked_parrot_voice_once
from carendmr.domain import TransmitHistoryEntry
from carendmr.encoder import DroidStarPluginEncoder

from .transmit_history_service import TransmitHistoryService


class ParrotTestService:
    def __init__(self, project_root: Path, *, audio_service, encoder_service) -> None:
        self.project_root = Path(project_root)
        self.audio_service = audio_service
        self.encoder_service = encoder_service
        self.history = TransmitHistoryService(self.project_root)

    def run_hold_to_talk(
        self,
        stop_event: Event,
        *,
        level_callback: Callable[[float], None] | None = None,
        optimize: bool = True,
    ) -> tuple[ParrotVoiceResult, float, bool]:
        plugin_path = self.encoder_service.configured_plugin_path
        if plugin_path is None:
            raise RuntimeError("Kein geprüftes DroidStar-Vocoder-Plugin konfiguriert.")
        self.encoder_service.verify_configured()
        started_at = datetime.now(timezone.utc).isoformat()
        pcm, duration, safety_limit_reached, _diagnostics = (
            self.audio_service.capture_transmit_pcm_until(
                stop_event,
                max_duration_seconds=float(self.audio_service.tx_safety_limit_seconds),
                level_callback=level_callback,
                optimize=optimize,
            )
        )
        if duration < 0.20:
            raise RuntimeError("Die TX-Taste wurde zu kurz gedrückt; es wurde nichts gesendet.")
        config = BrandMeisterConfigStore(
            self.project_root / "config" / "brandmeister.local.json"
        ).load()
        with DroidStarPluginEncoder(self.project_root, plugin_path) as encoder:
            result = execute_locked_parrot_voice_once(
                config, pcm_samples=pcm, encoder=encoder
            )
        self.history.add(TransmitHistoryEntry(
            started_at=started_at,
            duration_seconds=duration,
            destination_id=9990,
            timeslot=2,
            call_type="Privatruf",
            echo_received=result.echo_received,
            safety_limit_reached=safety_limit_reached,
            optimizer_enabled=optimize,
        ))
        return result, duration, safety_limit_reached
