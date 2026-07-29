"""Payloadfreie Ereignisgrenze für empfangene Homebrew-DMRD-Datagramme."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from .dmrd import (
    DmrdCallType,
    DmrdFrameClass,
    DmrdPacket,
    parse_dmrd_packet,
)


class DmrdReceiveActivity(Enum):
    """Für Status, Protokoll und spätere UI relevante Empfangsaktivität."""

    CALL_START = auto()
    VOICE = auto()
    CALL_END = auto()
    SIGNALING = auto()


@dataclass(frozen=True, slots=True)
class DmrdReceiveEvent:
    """Sichere Projektion eines DMRD-Pakets ohne Burst-Nutzdaten.

    ``stream_id`` ist ``None``, wenn der Absender im Homebrew-Feld null
    liefert. Call-/Frame-Metadaten bleiben trotzdem nutzbar.
    """

    sequence: int
    source_id: int
    destination_id: int
    timeslot: int
    call_type: DmrdCallType
    activity: DmrdReceiveActivity
    frame_class: DmrdFrameClass
    stream_id: int | None
    voice_frame_number: int | None
    data_type: int | None
    is_target_group: bool

    @classmethod
    def from_packet(cls, packet: DmrdPacket) -> "DmrdReceiveEvent":
        if packet.is_voice_lc_header:
            activity = DmrdReceiveActivity.CALL_START
        elif packet.is_terminator_with_lc:
            activity = DmrdReceiveActivity.CALL_END
        elif packet.frame_class in (
            DmrdFrameClass.VOICE,
            DmrdFrameClass.VOICE_SYNC,
        ):
            activity = DmrdReceiveActivity.VOICE
        else:
            activity = DmrdReceiveActivity.SIGNALING

        return cls(
            sequence=packet.sequence,
            source_id=packet.source_id,
            destination_id=packet.destination_id,
            timeslot=packet.timeslot,
            call_type=packet.call_type,
            activity=activity,
            frame_class=packet.frame_class,
            stream_id=packet.stream_id if packet.has_stream_id else None,
            voice_frame_number=packet.voice_frame_number,
            data_type=packet.data_type,
            is_target_group=packet.is_target_group,
        )


def parse_dmrd_receive_event(datagram: bytes) -> DmrdReceiveEvent:
    """Validiert ein Datagramm und erzeugt ein payloadfreies Empfangsereignis."""

    return DmrdReceiveEvent.from_packet(parse_dmrd_packet(datagram))
