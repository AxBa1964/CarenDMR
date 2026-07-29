"""Einmaliger, sicherheitsbegrenzter TG91/TS2-Stummruf mit Empfangsmonitor.

Dieses Diagnosewerkzeug besitzt absichtlich keine Parameter für Ziel,
Wiederholung, Paketinhalt, Laufzeit oder Sendeschleifen.
"""

from __future__ import annotations

import secrets
import sys
import time
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from carendmr.brandmeister import (
    SILENT_CALL_PACKET_COUNT,
    TARGET_TALKGROUP,
    TARGET_TIMESLOT,
    BrandMeisterClient,
    BrandMeisterConfig,
    BrandMeisterConfigStore,
    DmrdFrameClass,
    build_tg91_ts2_silent_call_fixture,
    parse_dmrd_packet,
)
from carendmr.brandmeister.protocol import LoginState
from carendmr.network import NetworkReceiveTimeout


CONFIG_PATH = PROJECT_ROOT / "config" / "brandmeister.local.json"
PACKET_INTERVAL_SECONDS = 0.060
MONITOR_SECONDS = 60.0


class OneShotSafetyError(RuntimeError):
    """Eine Sicherheitsbedingung verhindert oder beendet den Einmalversuch."""


class OneShotExecutionError(RuntimeError):
    """Fehler mit sicherer, nicht-sensitiver Ausführungsbilanz."""

    def __init__(
        self,
        *,
        authenticated: bool,
        sent_packets: int,
        closed: bool,
        cause_name: str,
    ) -> None:
        super().__init__("Der Einmalversuch wurde sicher abgebrochen.")
        self.authenticated = authenticated
        self.sent_packets = sent_packets
        self.closed = closed
        self.cause_name = cause_name


@dataclass(frozen=True, slots=True)
class MonitorCounts:
    total: int = 0
    dmrd: int = 0
    target_dmrd: int = 0
    other_control: int = 0
    invalid_dmrd: int = 0


@dataclass(frozen=True, slots=True)
class OneShotResult:
    authenticated: bool
    sent_packets: int
    sequence_complete: bool
    monitor: MonitorCounts
    closed: bool


def _validate_fixture(fixture, config: BrandMeisterConfig) -> None:
    packets = fixture.packets
    if len(packets) != SILENT_CALL_PACKET_COUNT:
        raise OneShotSafetyError("Die Fixture enthält nicht genau acht Pakete.")
    if any(
        packet.source_id != config.dmr_id
        or packet.repeater_id != config.dmr_id
        or packet.destination_id != TARGET_TALKGROUP
        or packet.timeslot != TARGET_TIMESLOT
        for packet in packets
    ):
        raise OneShotSafetyError("Eine feste TG91/TS2-Sicherheitsbedingung ist verletzt.")
    if not packets[0].is_voice_lc_header:
        raise OneShotSafetyError("Der erste Rahmen ist kein Voice-LC-Header.")
    if packets[1].frame_class is not DmrdFrameClass.VOICE_SYNC:
        raise OneShotSafetyError("Der zweite Rahmen ist kein Voice Sync.")
    if [packet.voice_frame_number for packet in packets[2:7]] != [1, 2, 3, 4, 5]:
        raise OneShotSafetyError("Die fünf Folgerahmen sind nicht exakt nummeriert.")
    if not packets[7].is_terminator_with_lc:
        raise OneShotSafetyError("Der letzte Rahmen ist kein Terminator-with-LC.")
    if len({packet.stream_id for packet in packets}) != 1:
        raise OneShotSafetyError("Die Fixture verwendet mehr als eine Stream-ID.")
    if any(len(packet.to_bytes()) != 55 for packet in packets):
        raise OneShotSafetyError("Mindestens ein DMRD-Paket ist nicht 55 Bytes lang.")


def _monitor(client: BrandMeisterClient, *, seconds: float, monotonic) -> MonitorCounts:
    deadline = monotonic() + seconds
    total = dmrd = target = control = invalid = 0
    while monotonic() < deadline:
        try:
            packet = client.transport.receive()
        except NetworkReceiveTimeout:
            continue

        total += 1
        if packet.startswith(b"DMRD"):
            try:
                parsed = parse_dmrd_packet(packet)
            except (TypeError, ValueError):
                invalid += 1
            else:
                dmrd += 1
                if parsed.is_target_group:
                    target += 1
        else:
            control += 1
    return MonitorCounts(total, dmrd, target, control, invalid)


def execute_one_shot(
    config: BrandMeisterConfig,
    *,
    client_factory=BrandMeisterClient,
    sleep=time.sleep,
    monotonic=time.monotonic,
    monitor_seconds: float = MONITOR_SECONDS,
    sequence_factory=lambda: secrets.randbelow(256),
    stream_factory=lambda: secrets.randbelow(0xFFFFFFFF) + 1,
) -> OneShotResult:
    """Authenticate, send the fixed sequence once, monitor, and always close."""

    if monitor_seconds <= 0 or monitor_seconds > MONITOR_SECONDS:
        raise OneShotSafetyError("Das Empfangsfenster muss zwischen 0 und 60 Sekunden liegen.")
    if config.dmr_id > 0xFFFFFF:
        raise OneShotSafetyError("Die konfigurierte DMR-ID passt nicht in das DMR-Quellfeld.")

    client = client_factory(config)
    authenticated = False
    sent_packets = 0
    complete = False
    monitor = MonitorCounts()
    closed = False
    error: Exception | None = None

    try:
        client.login()
        authenticated = client.state is LoginState.CONNECTED
        if not authenticated or client.transport is None:
            raise OneShotSafetyError("Die Anmeldung ist nicht eindeutig verbunden.")

        fixture = build_tg91_ts2_silent_call_fixture(
            source_id=config.dmr_id,
            repeater_id=config.dmr_id,
            stream_id=stream_factory(),
            first_sequence=sequence_factory(),
        )
        _validate_fixture(fixture, config)

        for index, packet in enumerate(fixture.to_bytes()):
            written = client.transport.send(packet)
            if written != len(packet):
                raise OneShotSafetyError("Ein DMRD-Paket wurde nicht vollständig gesendet.")
            sent_packets += 1
            if index + 1 < SILENT_CALL_PACKET_COUNT:
                sleep(PACKET_INTERVAL_SECONDS)
        complete = sent_packets == SILENT_CALL_PACKET_COUNT

        monitor = _monitor(client, seconds=monitor_seconds, monotonic=monotonic)
    except Exception as exc:
        error = exc
    finally:
        client.close()
        closed = client.transport is None and client.state is LoginState.DISCONNECTED

    if error is not None:
        raise OneShotExecutionError(
            authenticated=authenticated,
            sent_packets=sent_packets,
            closed=closed,
            cause_name=type(error).__name__,
        ) from error

    return OneShotResult(
        authenticated=authenticated,
        sent_packets=sent_packets,
        sequence_complete=complete,
        monitor=monitor,
        closed=closed,
    )


def main() -> int:
    try:
        config = BrandMeisterConfigStore(CONFIG_PATH).load()
        result = execute_one_shot(config)
    except OneShotExecutionError as exc:
        print(f"ABGEBROCHEN: {exc.cause_name}")
        print(f"Authentifiziert: {'ja' if exc.authenticated else 'nein'}")
        print(f"DMRD gesendet: {exc.sent_packets}/8")
        print(f"Kanal geschlossen: {'ja' if exc.closed else 'nein'}")
        print("Keine Wiederholung wurde versucht.")
        return 2
    except Exception as exc:
        # Never print configuration, identifiers, endpoints, packets or secrets.
        print(f"ABGEBROCHEN: {type(exc).__name__}")
        print("DMRD gesendet: 0/8")
        print("Keine Wiederholung wurde versucht.")
        return 2

    print("Einmaliger TG91/TS2-Stummruf abgeschlossen.")
    print(f"Authentifiziert: {'ja' if result.authenticated else 'nein'}")
    print(f"DMRD gesendet: {result.sent_packets}/8")
    print(f"Sequenz vollständig: {'ja' if result.sequence_complete else 'nein'}")
    print(f"Empfang gesamt: {result.monitor.total}")
    print(f"Empfang DMRD: {result.monitor.dmrd}")
    print(f"Empfang Ziel-TG91/TS2: {result.monitor.target_dmrd}")
    print(f"Empfang sonstige Steuerpakete: {result.monitor.other_control}")
    print(f"Empfang ungültige DMRD: {result.monitor.invalid_dmrd}")
    print(f"Kanal geschlossen: {'ja' if result.closed else 'nein'}")
    return 0 if result.sequence_complete and result.closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
