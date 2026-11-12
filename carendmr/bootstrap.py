"""Gemeinsamer Startpunkt (Composition Root) für alle CarenDMR-Oberflächen.

Hier wird der Funkkern genau einmal und für jede Oberfläche identisch
zusammengesetzt: Ereignisse, Empfang, Encoder, Audio, Parrot,
ConnectionManager und OperatingController. Hauptfenster und Easy-Oberfläche
erhalten den fertigen Kern und bauen keine eigene Funk-Verdrahtung mehr auf.

Das Modul ist bewusst Qt-frei, damit spätere Oberflächen (Konsole,
Hardwarebedienung, Android) denselben Kern verwenden können.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from carendmr.application import (
    AudioSendService,
    ConnectionManager,
    EncoderService,
    EventService,
    OperatingController,
    ParrotTestService,
    ReceiveService,
)


@dataclass(frozen=True)
class RadioCore:
    """Der vollständig verdrahtete Funkkern einer CarenDMR-Sitzung."""

    project_root: Path
    events: EventService
    receive_service: ReceiveService
    encoder_service: EncoderService
    audio_send_service: AudioSendService
    parrot_service: ParrotTestService
    connection_manager: ConnectionManager
    controller: OperatingController


def build_radio_core(project_root: Path, *, audio_backend=None) -> RadioCore:
    """Setzt den Funkkern zusammen.

    ``audio_backend`` ist nur für Tests gedacht; im Betrieb verwendet der
    AudioSendService sein sounddevice-Backend.
    """
    root = Path(project_root)
    events = EventService()
    receive_service = ReceiveService(root, events=events)
    encoder_service = EncoderService(root)
    audio_send_service = AudioSendService(
        root,
        backend=audio_backend,
        mute_receive=receive_service.mute_audio_output,
        unmute_receive=receive_service.unmute_audio_output,
    )
    receive_service.set_output_factory(audio_send_service.create_pcm_output)
    # Gespeicherte Audioeinstellungen müssen nicht nur im UI stehen, sondern
    # beim Start auch tatsächlich im RX-Dienst gelten.
    receive_service.set_output_volume_percent(audio_send_service.output_volume_percent)
    receive_service.set_user_muted(audio_send_service.user_muted)
    # 0.2.1.45 Diagnose: RX-AGC startet bewusst AUS, um den beobachteten
    # leisen/hochregelnden Gesprächsanfang eindeutig gegenprüfen zu können.
    # Der Benutzer kann AGC während der Sitzung weiterhin manuell einschalten.
    audio_send_service.set_agc_enabled(False)
    receive_service.set_agc_enabled(False)
    receive_service.set_audio_debug_enabled(audio_send_service.audio_debug_wav_enabled)
    receive_service.set_audio_debug_dir_provider(lambda: audio_send_service.audio_test_session_dir)
    parrot_service = ParrotTestService(
        root,
        audio_service=audio_send_service,
        encoder_service=encoder_service,
    )
    connection_manager = ConnectionManager(receive_service, parrot_service, events=events)
    controller = OperatingController(connection_manager, receive_service)
    return RadioCore(
        project_root=root,
        events=events,
        receive_service=receive_service,
        encoder_service=encoder_service,
        audio_send_service=audio_send_service,
        parrot_service=parrot_service,
        connection_manager=connection_manager,
        controller=controller,
    )
