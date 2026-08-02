"""Hard-locked offline foundation for a future BrandMeister Parrot test."""

from __future__ import annotations

from dataclasses import dataclass

from .dmrd import (
    DmrdCallType,
    DmrdDataType,
    DmrdFrameClass,
    DmrdPacket,
)
from .silent_call import (
    SILENT_CALL_PACKET_COUNT,
    SILENT_VOICE_BURST_COUNT,
    SilentCallFixture,
    _encode_embedded_lc,
    _encode_full_lc_burst,
    _encode_voice_burst,
    _encode_voice_sync_burst,
)


PARROT_DESTINATION_ID = 9990
PARROT_TIMESLOT = 2
PARROT_TRANSMIT_CAP_SECONDS = 180.0
PARROT_ECHO_CAP_SECONDS = 15.0
PARROT_FIXTURE_SECONDS = SILENT_VOICE_BURST_COUNT * 0.060

_FLCO_PRIVATE_USER_TO_USER = 0x03
_VOICE_LC_HEADER = 0x01
_TERMINATOR_WITH_LC = 0x02


@dataclass(frozen=True, slots=True)
class LockedParrotTestProfile:
    """Non-configurable safety policy for a future controlled live test."""

    destination_id: int = PARROT_DESTINATION_ID
    timeslot: int = PARROT_TIMESLOT
    call_type: DmrdCallType = DmrdCallType.PRIVATE
    transmit_cap_seconds: float = PARROT_TRANSMIT_CAP_SECONDS
    echo_cap_seconds: float = PARROT_ECHO_CAP_SECONDS

    def validate(self) -> None:
        if (
            self.destination_id != PARROT_DESTINATION_ID
            or self.timeslot != PARROT_TIMESLOT
            or self.call_type is not DmrdCallType.PRIVATE
            or self.transmit_cap_seconds != PARROT_TRANSMIT_CAP_SECONDS
            or self.echo_cap_seconds != PARROT_ECHO_CAP_SECONDS
        ):
            raise ParrotSafetyError("Das Parrot-Testprofil wurde verändert.")


LOCKED_PARROT_PROFILE = LockedParrotTestProfile()


class ParrotSafetyError(RuntimeError):
    """A hard Parrot safety condition is not satisfied."""


@dataclass(frozen=True, slots=True)
class ParrotTestPlan:
    """Validated offline plan; deliberately has no execute/send method."""

    profile: LockedParrotTestProfile
    fixture: SilentCallFixture
    transmit_seconds: float
    echo_observation_seconds: float

    def __post_init__(self) -> None:
        validate_parrot_test_plan(self)


def build_locked_parrot_fixture(
    *,
    source_id: int,
    repeater_id: int,
    stream_id: int,
    first_sequence: int = 0,
) -> SilentCallFixture:
    """Build one silent private-call fixture with no target/timing arguments."""

    if not isinstance(first_sequence, int) or isinstance(first_sequence, bool):
        raise TypeError("Die erste Sequenznummer muss eine ganze Zahl sein.")
    if not 0 <= first_sequence <= 0xFF:
        raise ValueError("Die erste Sequenznummer muss zwischen 0 und 255 liegen.")
    if not isinstance(source_id, int) or isinstance(source_id, bool):
        raise TypeError("Quell-ID muss eine ganze Zahl sein.")
    if not 1 <= source_id <= 0xFFFFFF:
        raise ValueError("Quell-ID muss zwischen 1 und 16777215 liegen.")
    if not isinstance(stream_id, int) or isinstance(stream_id, bool):
        raise TypeError("Stream-ID muss eine ganze Zahl sein.")
    if not 1 <= stream_id <= 0xFFFFFFFF:
        raise ValueError("Stream-ID muss zwischen 1 und 4294967295 liegen.")

    link_control = (
        bytes((_FLCO_PRIVATE_USER_TO_USER, 0, 0))
        + PARROT_DESTINATION_ID.to_bytes(3, "big")
        + source_id.to_bytes(3, "big")
    )
    embedded = _encode_embedded_lc(link_control)
    payloads = (
        _encode_full_lc_burst(link_control, _VOICE_LC_HEADER),
        _encode_voice_sync_burst(),
        *(_encode_voice_burst(number, embedded) for number in range(1, 6)),
        _encode_full_lc_burst(link_control, _TERMINATOR_WITH_LC),
    )
    sequences = tuple((first_sequence + offset) & 0xFF for offset in range(8))

    packets = tuple(
        DmrdPacket(
            sequence=sequences[index],
            source_id=source_id,
            destination_id=PARROT_DESTINATION_ID,
            repeater_id=repeater_id,
            timeslot=PARROT_TIMESLOT,
            call_type=DmrdCallType.PRIVATE,
            frame_class=(
                DmrdFrameClass.DATA_SYNC
                if index in (0, 7)
                else DmrdFrameClass.VOICE_SYNC
                if index == 1
                else DmrdFrameClass.VOICE
            ),
            stream_id=stream_id,
            payload=payloads[index],
            voice_frame_number=index - 1 if 2 <= index <= 6 else None,
            data_type=(
                DmrdDataType.VOICE_LC_HEADER.value
                if index == 0
                else DmrdDataType.TERMINATOR_WITH_LC.value
                if index == 7
                else None
            ),
        )
        for index in range(SILENT_CALL_PACKET_COUNT)
    )
    fixture = SilentCallFixture(packets)
    validate_locked_parrot_fixture(fixture)
    return fixture


def build_locked_parrot_test_plan(
    *,
    source_id: int,
    repeater_id: int,
    stream_id: int,
    first_sequence: int = 0,
) -> ParrotTestPlan:
    return ParrotTestPlan(
        profile=LOCKED_PARROT_PROFILE,
        fixture=build_locked_parrot_fixture(
            source_id=source_id,
            repeater_id=repeater_id,
            stream_id=stream_id,
            first_sequence=first_sequence,
        ),
        transmit_seconds=PARROT_FIXTURE_SECONDS,
        echo_observation_seconds=PARROT_ECHO_CAP_SECONDS,
    )


def validate_locked_parrot_fixture(fixture: SilentCallFixture) -> None:
    if len(fixture.packets) != SILENT_CALL_PACKET_COUNT:
        raise ParrotSafetyError("Die Parrot-Fixture muss genau acht Pakete enthalten.")
    for packet in fixture.packets:
        raw = packet.to_bytes()
        if (
            packet.destination_id != PARROT_DESTINATION_ID
            or packet.timeslot != PARROT_TIMESLOT
            or packet.call_type is not DmrdCallType.PRIVATE
            or not raw[15] & 0x40
        ):
            raise ParrotSafetyError(
                "Ziel, Privatrufkennzeichen oder Timeslot ist nicht fest verriegelt."
            )
    if not fixture.packets[0].is_voice_lc_header:
        raise ParrotSafetyError("Der Parrot-Ruf beginnt nicht mit Voice-LC.")
    if not fixture.packets[-1].is_terminator_with_lc:
        raise ParrotSafetyError("Der Parrot-Ruf endet nicht mit Terminator-LC.")


def validate_parrot_test_plan(plan: ParrotTestPlan) -> None:
    plan.profile.validate()
    validate_locked_parrot_fixture(plan.fixture)
    if plan.transmit_seconds > PARROT_TRANSMIT_CAP_SECONDS:
        raise ParrotSafetyError("Die feste Sendezeit überschreitet hundertachtzig Sekunden.")
    if plan.echo_observation_seconds != PARROT_ECHO_CAP_SECONDS:
        raise ParrotSafetyError("Das Echo-Fenster ist nicht exakt auf 180 Sekunden verriegelt.")
    if hasattr(plan, "send") or hasattr(plan, "execute"):
        raise ParrotSafetyError("Der Offline-Plan darf keine Sendefunktion besitzen.")
