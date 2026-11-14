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

from carendmr.accessibility.hotkeys import HotkeyManager
from carendmr.adif_udp import AdifUdpService
from carendmr.application import (
    AudioSendService,
    ConnectionManager,
    EncoderService,
    EventService,
    FavoriteService,
    LocalAudioLabService,
    OperatingController,
    ParrotTestService,
    QsoRecordingService,
    ReceiveService,
    TalkgroupCatalogService,
    TalkgroupSearchService,
)
from carendmr.application.audio_setup_service import AudioSetupService
from carendmr.application.codec_setup_service import CodecSetupService
from carendmr.application.contact_service import ContactService
from carendmr.application.station_settings_service import StationSettingsService
from carendmr.benchmark import AudioBenchmarkService
from carendmr.qrz import QrzLogbookService, QrzLookupService


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


@dataclass(frozen=True)
class DesktopServices:
    """Zusatzdienste der Desktop-Oberfläche rund um den Funkkern.

    QRZ, Logbuch, ADIF, Favoriten, Talkgroup-Verzeichnis, Hotkeys, Mitschnitt,
    Audio-Labor und Benchmark werden hier statt im Hauptfenster erzeugt.
    """

    station_settings: StationSettingsService
    local_audio_lab: LocalAudioLabService
    qso_recording: QsoRecordingService
    qrz_lookup: QrzLookupService
    qrz_logbook: QrzLogbookService
    adif_udp: AdifUdpService
    hotkeys: HotkeyManager
    favorites: FavoriteService
    talkgroup_search: TalkgroupSearchService
    talkgroup_catalog: TalkgroupCatalogService
    audio_benchmark: AudioBenchmarkService
    codec_setup: CodecSetupService


@dataclass(frozen=True)
class FirstRunServices:
    """Dienste für die Ersteinrichtung vor dem Öffnen eines Fensters."""

    station_settings: StationSettingsService
    codec_setup: CodecSetupService
    audio_setup: AudioSetupService
    contacts: ContactService


def build_first_run_services(project_root: Path, *, audio_manager=None) -> FirstRunServices:
    """Einrichtungsdienste; ``audio_manager`` eines laufenden Funkkerns optional."""
    return FirstRunServices(
        station_settings=StationSettingsService(project_root),
        codec_setup=CodecSetupService(project_root),
        audio_setup=AudioSetupService(project_root, audio_manager),
        contacts=ContactService(project_root),
    )


def build_desktop_services(core: RadioCore) -> DesktopServices:
    """Setzt die Desktop-Zusatzdienste für einen bestehenden Funkkern zusammen."""
    root = core.project_root
    config = root / "config"
    local_audio_lab = LocalAudioLabService(root, core.audio_send_service, core.encoder_service)
    qso_recording = QsoRecordingService(root)
    # Gesendetes Audio landet auch im QSO-Mitschnitt.
    core.audio_send_service.set_tx_pcm_observer(qso_recording.add_tx)
    favorites = FavoriteService(config / "favorites.local.json")
    talkgroup_search = TalkgroupSearchService(config / "talkgroups.json")
    talkgroup_search.set_favorites(favorites.favorites)
    return DesktopServices(
        station_settings=StationSettingsService(root),
        local_audio_lab=local_audio_lab,
        qso_recording=qso_recording,
        qrz_lookup=QrzLookupService(config / "qrz.local.json"),
        qrz_logbook=QrzLogbookService(config / "qrz_logbook.local.json"),
        adif_udp=AdifUdpService(config / "adif_udp.local.json"),
        hotkeys=HotkeyManager(config / "hotkeys.local.json"),
        favorites=favorites,
        talkgroup_search=talkgroup_search,
        talkgroup_catalog=TalkgroupCatalogService(config / "talkgroups.json"),
        audio_benchmark=AudioBenchmarkService(root, contact_lookup=core.receive_service.contacts.lookup),
        codec_setup=CodecSetupService(root),
    )
