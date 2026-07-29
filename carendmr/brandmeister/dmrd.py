"""DMRD-Paketmodell ohne Netzwerk- oder Audio-Seiteneffekte."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


DMRD_PACKET_SIZE = 55
DMRD_PAYLOAD_SIZE = 33
TARGET_TALKGROUP = 91
TARGET_TIMESLOT = 2

_TAG = b"DMRD"
_SLOT_2_MASK = 0x80
_PRIVATE_CALL_MASK = 0x40
_FRAME_CLASS_MASK = 0x30
_VOICE_SYNC_MASK = 0x10
_DATA_SYNC_MASK = 0x20
_SUBTYPE_MASK = 0x0F


class DmrdCallType(Enum):
    GROUP = auto()
    PRIVATE = auto()


class DmrdFrameClass(Enum):
    VOICE = auto()
    VOICE_SYNC = auto()
    DATA_SYNC = auto()


class DmrdDataType(Enum):
    VOICE_LC_HEADER = 0x01
    TERMINATOR_WITH_LC = 0x02


def _require_range(name: str, value: int, minimum: int, maximum: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} muss eine ganze Zahl sein.")
    if not minimum <= value <= maximum:
        raise ValueError(
            f"{name} muss zwischen {minimum} und {maximum} liegen."
        )


def _three_bytes(value: int) -> bytes:
    return value.to_bytes(3, byteorder="big", signed=False)


@dataclass(frozen=True, slots=True)
class DmrdPacket:
    """Unveränderliche Darstellung eines 55-Byte-Homebrew-DMRD-Pakets."""

    sequence: int
    source_id: int
    destination_id: int
    repeater_id: int
    timeslot: int
    call_type: DmrdCallType
    frame_class: DmrdFrameClass
    stream_id: int
    payload: bytes
    ber: int = 0
    rssi: int = 0
    voice_frame_number: int | None = None
    data_type: int | None = None

    def __post_init__(self) -> None:
        _require_range("Sequenznummer", self.sequence, 0, 0xFF)
        _require_range("Quell-ID", self.source_id, 1, 0xFFFFFF)
        _require_range("Ziel-ID", self.destination_id, 1, 0xFFFFFF)
        _require_range("Repeater-ID", self.repeater_id, 1, 0xFFFFFFFF)
        _require_range("Zeitschlitz", self.timeslot, 1, 2)
        _require_range("Stream-ID", self.stream_id, 1, 0xFFFFFFFF)
        _require_range("BER", self.ber, 0, 0xFF)
        _require_range("RSSI", self.rssi, 0, 0xFF)

        if not isinstance(self.call_type, DmrdCallType):
            raise TypeError("Der Ruftyp ist ungültig.")
        if not isinstance(self.frame_class, DmrdFrameClass):
            raise TypeError("Die Rahmenklasse ist ungültig.")
        if not isinstance(self.payload, bytes):
            raise TypeError("Die DMR-Nutzdaten müssen bytes sein.")
        if len(self.payload) != DMRD_PAYLOAD_SIZE:
            raise ValueError(
                f"Die DMR-Nutzdaten müssen genau {DMRD_PAYLOAD_SIZE} Bytes lang sein."
            )

        if self.frame_class is DmrdFrameClass.VOICE:
            if self.voice_frame_number is None:
                raise ValueError("Ein Sprachrahmen benötigt eine Rahmennummer.")
            _require_range(
                "Sprachrahmennummer",
                self.voice_frame_number,
                0,
                5,
            )
            if self.data_type is not None:
                raise ValueError("Ein Sprachrahmen darf keinen Datentyp tragen.")
        elif self.frame_class is DmrdFrameClass.VOICE_SYNC:
            if self.voice_frame_number is not None or self.data_type is not None:
                raise ValueError(
                    "Ein Sprach-Synchronrahmen hat weder Rahmennummer noch Datentyp."
                )
        else:
            if self.voice_frame_number is not None:
                raise ValueError(
                    "Ein Daten-Synchronrahmen darf keine Sprachrahmennummer tragen."
                )
            if self.data_type is None:
                raise ValueError("Ein Daten-Synchronrahmen benötigt einen Datentyp.")
            _require_range("DMR-Datentyp", self.data_type, 0, _SUBTYPE_MASK)

    @property
    def is_target_group(self) -> bool:
        return (
            self.call_type is DmrdCallType.GROUP
            and self.destination_id == TARGET_TALKGROUP
            and self.timeslot == TARGET_TIMESLOT
        )

    @property
    def is_voice_lc_header(self) -> bool:
        return (
            self.frame_class is DmrdFrameClass.DATA_SYNC
            and self.data_type == DmrdDataType.VOICE_LC_HEADER.value
        )

    @property
    def is_terminator_with_lc(self) -> bool:
        return (
            self.frame_class is DmrdFrameClass.DATA_SYNC
            and self.data_type == DmrdDataType.TERMINATOR_WITH_LC.value
        )

    def to_bytes(self) -> bytes:
        flags = _encode_flags(self)
        packet = b"".join(
            (
                _TAG,
                bytes((self.sequence,)),
                _three_bytes(self.source_id),
                _three_bytes(self.destination_id),
                self.repeater_id.to_bytes(4, byteorder="big", signed=False),
                bytes((flags,)),
                self.stream_id.to_bytes(4, byteorder="big", signed=False),
                self.payload,
                bytes((self.ber, self.rssi)),
            )
        )
        if len(packet) != DMRD_PACKET_SIZE:
            raise AssertionError(
                f"Internes Formatproblem: DMRD hat {len(packet)} "
                f"statt {DMRD_PACKET_SIZE} Bytes."
            )
        return packet


def _encode_flags(packet: DmrdPacket) -> int:
    flags = _SLOT_2_MASK if packet.timeslot == 2 else 0
    if packet.call_type is DmrdCallType.PRIVATE:
        flags |= _PRIVATE_CALL_MASK

    if packet.frame_class is DmrdFrameClass.VOICE:
        return flags | int(packet.voice_frame_number)
    if packet.frame_class is DmrdFrameClass.VOICE_SYNC:
        return flags | _VOICE_SYNC_MASK
    return flags | _DATA_SYNC_MASK | int(packet.data_type)


def parse_dmrd_packet(packet: bytes) -> DmrdPacket:
    """Prüft und zerlegt ein vollständiges 55-Byte-DMRD-Paket."""

    if not isinstance(packet, bytes):
        raise TypeError("Das DMRD-Paket muss bytes sein.")
    if len(packet) != DMRD_PACKET_SIZE:
        raise ValueError(
            f"Ein DMRD-Paket muss genau {DMRD_PACKET_SIZE} Bytes lang sein."
        )
    if packet[:4] != _TAG:
        raise ValueError("Das Paket beginnt nicht mit der DMRD-Kennung.")

    flags = packet[15]
    frame_bits = flags & _FRAME_CLASS_MASK
    subtype = flags & _SUBTYPE_MASK
    voice_frame_number: int | None = None
    data_type: int | None = None

    if frame_bits == 0:
        if subtype > 5:
            raise ValueError("Die DMRD-Sprachrahmennummer ist ungültig.")
        frame_class = DmrdFrameClass.VOICE
        voice_frame_number = subtype
    elif frame_bits == _VOICE_SYNC_MASK:
        if subtype != 0:
            raise ValueError("Ein DMRD-Sprach-Synchronrahmen hat reservierte Bits.")
        frame_class = DmrdFrameClass.VOICE_SYNC
    elif frame_bits == _DATA_SYNC_MASK:
        frame_class = DmrdFrameClass.DATA_SYNC
        data_type = subtype
    else:
        raise ValueError("Die DMRD-Rahmenklasse ist reserviert.")

    return DmrdPacket(
        sequence=packet[4],
        source_id=int.from_bytes(packet[5:8], byteorder="big"),
        destination_id=int.from_bytes(packet[8:11], byteorder="big"),
        repeater_id=int.from_bytes(packet[11:15], byteorder="big"),
        timeslot=2 if flags & _SLOT_2_MASK else 1,
        call_type=(
            DmrdCallType.PRIVATE
            if flags & _PRIVATE_CALL_MASK
            else DmrdCallType.GROUP
        ),
        frame_class=frame_class,
        stream_id=int.from_bytes(packet[16:20], byteorder="big"),
        payload=packet[20:53],
        ber=packet[53],
        rssi=packet[54],
        voice_frame_number=voice_frame_number,
        data_type=data_type,
    )


def build_tg91_voice_lc_header(
    *,
    sequence: int,
    source_id: int,
    repeater_id: int,
    stream_id: int,
    payload: bytes,
) -> DmrdPacket:
    return _build_target_packet(
        sequence=sequence,
        source_id=source_id,
        repeater_id=repeater_id,
        stream_id=stream_id,
        payload=payload,
        frame_class=DmrdFrameClass.DATA_SYNC,
        data_type=DmrdDataType.VOICE_LC_HEADER.value,
    )


def build_tg91_voice_sync(
    *,
    sequence: int,
    source_id: int,
    repeater_id: int,
    stream_id: int,
    payload: bytes,
) -> DmrdPacket:
    return _build_target_packet(
        sequence=sequence,
        source_id=source_id,
        repeater_id=repeater_id,
        stream_id=stream_id,
        payload=payload,
        frame_class=DmrdFrameClass.VOICE_SYNC,
    )


def build_tg91_voice_frame(
    *,
    sequence: int,
    source_id: int,
    repeater_id: int,
    stream_id: int,
    voice_frame_number: int,
    payload: bytes,
) -> DmrdPacket:
    return _build_target_packet(
        sequence=sequence,
        source_id=source_id,
        repeater_id=repeater_id,
        stream_id=stream_id,
        payload=payload,
        frame_class=DmrdFrameClass.VOICE,
        voice_frame_number=voice_frame_number,
    )


def build_tg91_terminator_with_lc(
    *,
    sequence: int,
    source_id: int,
    repeater_id: int,
    stream_id: int,
    payload: bytes,
) -> DmrdPacket:
    return _build_target_packet(
        sequence=sequence,
        source_id=source_id,
        repeater_id=repeater_id,
        stream_id=stream_id,
        payload=payload,
        frame_class=DmrdFrameClass.DATA_SYNC,
        data_type=DmrdDataType.TERMINATOR_WITH_LC.value,
    )


def _build_target_packet(
    *,
    sequence: int,
    source_id: int,
    repeater_id: int,
    stream_id: int,
    payload: bytes,
    frame_class: DmrdFrameClass,
    voice_frame_number: int | None = None,
    data_type: int | None = None,
) -> DmrdPacket:
    return DmrdPacket(
        sequence=sequence,
        source_id=source_id,
        destination_id=TARGET_TALKGROUP,
        repeater_id=repeater_id,
        timeslot=TARGET_TIMESLOT,
        call_type=DmrdCallType.GROUP,
        frame_class=frame_class,
        stream_id=stream_id,
        payload=payload,
        voice_frame_number=voice_frame_number,
        data_type=data_type,
    )
