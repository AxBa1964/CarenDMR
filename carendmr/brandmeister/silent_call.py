"""Deterministische, rein offline erzeugte DMR-Stummruf-Fixture.

Copyright (C) 2019-2021 Doug McLain
Copyright (C) 2012 Ian Wraith
Copyright (C) 2015-2016 Jonathan Naylor G4KLX
Copyright (C) 2018 Andy Uribe CA6JAU
Copyright (C) 2026 CarenDMR contributors

This file is a Python adaptation of the minimal DMR encoding path in
DroidStar. It is distributed under the GNU General Public License, version
3 or (at your option) any later version. See LICENSE and
docs/UPSTREAM_PROVENANCE.md.

The module deliberately exposes no socket, client, keying, timing, audio or
general transmit API. It can only construct one fixed TG91/Timeslot-2 group
call containing a Voice-LC header, one six-burst silent superframe and a
Terminator-with-LC.
"""

from __future__ import annotations

from dataclasses import dataclass
import sys

from .dmrd import (
    DMRD_PAYLOAD_SIZE,
    DmrdCallType,
    DmrdDataType,
    DmrdFrameClass,
    DmrdPacket,
    build_tg91_terminator_with_lc,
    build_tg91_voice_frame,
    build_tg91_voice_lc_header,
    build_tg91_voice_sync,
)


SILENT_CALL_PACKET_COUNT = 8
SILENT_VOICE_BURST_COUNT = 6

_COLOR_CODE = 0 if sys.platform == "darwin" else 1
_VOICE_LC_HEADER = 0x01
_TERMINATOR_WITH_LC = 0x02
_VOICE_LC_CRC_MASK = 0x96
_TERMINATOR_LC_CRC_MASK = 0x99

_MS_DATA_SYNC = bytes((0x0D, 0x5D, 0x7F, 0x77, 0xFD, 0x75, 0x70))
_MS_AUDIO_SYNC = bytes((0x07, 0xF7, 0xD5, 0xDD, 0x57, 0xDF, 0xD0))
_SYNC_MASK = bytes((0x0F, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xF0))

# Three AMBE+2 silence codewords in the 33-byte DMR burst layout used by
# DroidStar/MMDVM. This is a fixed reference vector, not a software vocoder.
_DMR_SILENCE_DATA = bytes.fromhex(
    "b9e881526173002a6bb9e881526000000000000173002a6b"
    "b9e881526173002a6b"
)

# QR(16,7,6) reference values used by the deliberately fixed colour code 1
# and LCSS values 0..3. Keeping this surface constrained avoids importing
# DroidStar's unrelated general-purpose tables.
_EMB_CODEWORDS_CC0 = (0x0000, 0x0273, 0x04E5, 0x0696)
_EMB_CODEWORDS_CC1 = (0x11E2, 0x1391, 0x1507, 0x1774)
_EMB_CODEWORDS = _EMB_CODEWORDS_CC0 if sys.platform == "darwin" else _EMB_CODEWORDS_CC1


@dataclass(frozen=True, slots=True)
class SilentCallFixture:
    """The eight immutable DMRD packets of one silent TG91/TS2 call."""

    packets: tuple[DmrdPacket, ...]

    def __post_init__(self) -> None:
        if len(self.packets) != SILENT_CALL_PACKET_COUNT:
            raise ValueError("Eine Stummruf-Fixture muss genau 8 Pakete enthalten.")

    def to_bytes(self) -> tuple[bytes, ...]:
        return tuple(packet.to_bytes() for packet in self.packets)


def build_silent_call_fixture(
    *,
    source_id: int,
    repeater_id: int,
    destination_id: int,
    timeslot: int,
    stream_id: int,
    call_type: DmrdCallType = DmrdCallType.GROUP,
    first_sequence: int = 0,
) -> SilentCallFixture:
    """Build a complete valid silent group or private call."""

    if not isinstance(first_sequence, int) or isinstance(first_sequence, bool):
        raise TypeError("Die erste Sequenznummer muss eine ganze Zahl sein.")
    if not 0 <= first_sequence <= 0xFF:
        raise ValueError("Die erste Sequenznummer muss zwischen 0 und 255 liegen.")
    if not 1 <= source_id <= 0xFFFFFF:
        raise ValueError("Quell-ID muss zwischen 1 und 16777215 liegen.")
    if not 1 <= repeater_id <= 0xFFFFFFFF:
        raise ValueError("Repeater-ID muss zwischen 1 und 4294967295 liegen.")
    if not 1 <= stream_id <= 0xFFFFFFFF:
        raise ValueError("Stream-ID muss zwischen 1 und 4294967295 liegen.")
    if not 1 <= destination_id <= 0xFFFFFF:
        raise ValueError("Ziel-ID muss zwischen 1 und 16777215 liegen.")
    if not isinstance(call_type, DmrdCallType):
        raise TypeError("Die Rufart muss GROUP oder PRIVATE sein.")
    if timeslot not in (1, 2):
        raise ValueError("Timeslot muss 1 oder 2 sein.")

    flco = 0x03 if call_type is DmrdCallType.PRIVATE else 0x00
    lc = bytes((flco, 0, 0)) + destination_id.to_bytes(3, "big") + source_id.to_bytes(3, "big")
    embedded = _encode_embedded_lc(lc)
    payloads = (
        _encode_full_lc_burst(lc, _VOICE_LC_HEADER),
        _encode_voice_sync_burst(),
        *(_encode_voice_burst(number, embedded) for number in range(1, 6)),
        _encode_full_lc_burst(lc, _TERMINATOR_WITH_LC),
    )
    sequence = tuple((first_sequence + offset) & 0xFF for offset in range(8))

    packets = (
        DmrdPacket(sequence[0], source_id, destination_id, repeater_id, timeslot,
                   call_type, DmrdFrameClass.DATA_SYNC, stream_id,
                   payloads[0], data_type=DmrdDataType.VOICE_LC_HEADER.value),
        DmrdPacket(sequence[1], source_id, destination_id, repeater_id, timeslot,
                   call_type, DmrdFrameClass.VOICE_SYNC, stream_id, payloads[1]),
        *(
            DmrdPacket(sequence[number + 1], source_id, destination_id, repeater_id, timeslot,
                       call_type, DmrdFrameClass.VOICE, stream_id,
                       payloads[number + 1], voice_frame_number=number)
            for number in range(1, 6)
        ),
        DmrdPacket(sequence[7], source_id, destination_id, repeater_id, timeslot,
                   call_type, DmrdFrameClass.DATA_SYNC, stream_id,
                   payloads[7], data_type=DmrdDataType.TERMINATOR_WITH_LC.value),
    )
    return SilentCallFixture(packets=packets)


def build_silent_group_call_fixture(
    *, source_id: int, repeater_id: int, talkgroup: int, timeslot: int,
    stream_id: int, first_sequence: int = 0
) -> SilentCallFixture:
    """Compatibility wrapper for a dynamic group call."""
    return build_silent_call_fixture(
        source_id=source_id, repeater_id=repeater_id,
        destination_id=talkgroup, timeslot=timeslot, stream_id=stream_id,
        call_type=DmrdCallType.GROUP, first_sequence=first_sequence,
    )


def build_tg91_ts2_silent_call_fixture(
    *, source_id: int, repeater_id: int, stream_id: int, first_sequence: int = 0
) -> SilentCallFixture:
    """Compatibility wrapper for the original locked TG91/TS2 fixture."""
    return build_silent_group_call_fixture(
        source_id=source_id, repeater_id=repeater_id, talkgroup=91, timeslot=2,
        stream_id=stream_id, first_sequence=first_sequence,
    )

def _link_control(source_id: int) -> bytes:
    if not isinstance(source_id, int) or isinstance(source_id, bool):
        raise TypeError("Quell-ID muss eine ganze Zahl sein.")
    if not 1 <= source_id <= 0xFFFFFF:
        raise ValueError("Quell-ID muss zwischen 1 und 16777215 liegen.")
    return bytes((0, 0, 0, 0, 0, 91)) + source_id.to_bytes(3, "big")


def _encode_full_lc_burst(link_control: bytes, data_type: int) -> bytes:
    crc_mask = (
        _VOICE_LC_CRC_MASK
        if data_type == _VOICE_LC_HEADER
        else _TERMINATOR_LC_CRC_MASK
    )
    parity = _rs129_parity(link_control)
    lc_data = link_control + bytes(
        (parity[2] ^ crc_mask, parity[1] ^ crc_mask, parity[0] ^ crc_mask)
    )

    burst = bytearray(DMRD_PAYLOAD_SIZE)
    _add_sync(burst, _MS_DATA_SYNC)
    _add_slot_type(burst, data_type)
    _encode_bptc_196_96(lc_data, burst)
    return bytes(burst)


def _encode_voice_sync_burst() -> bytes:
    burst = bytearray(_DMR_SILENCE_DATA)
    _add_sync(burst, _MS_AUDIO_SYNC)
    return bytes(burst)


def _encode_voice_burst(number: int, embedded: tuple[bool, ...]) -> bytes:
    burst = bytearray(_DMR_SILENCE_DATA)
    lcss = 0

    if 1 <= number < 5:
        fragment = embedded[(number - 1) * 32 : number * 32]
        packed = _bits_to_bytes((False,) * 4 + fragment + (False,) * 4)
        burst[14] = (burst[14] & 0xF0) | (packed[0] & 0x0F)
        burst[15:18] = packed[1:4]
        burst[18] = (burst[18] & 0x0F) | (packed[4] & 0xF0)
        lcss = 1 if number == 1 else 2 if number == 4 else 3
    else:
        burst[14] &= 0xF0
        burst[15:18] = b"\x00\x00\x00"
        burst[18] &= 0x0F

    codeword = _EMB_CODEWORDS[lcss]
    emb0, emb1 = codeword >> 8, codeword & 0xFF
    burst[13] = (burst[13] & 0xF0) | ((emb0 >> 4) & 0x0F)
    burst[14] = (burst[14] & 0x0F) | ((emb0 << 4) & 0xF0)
    burst[18] = (burst[18] & 0xF0) | ((emb1 >> 4) & 0x0F)
    burst[19] = (burst[19] & 0x0F) | ((emb1 << 4) & 0xF0)
    return bytes(burst)


def _add_sync(burst: bytearray, sync: bytes) -> None:
    for offset, (value, mask) in enumerate(zip(sync, _SYNC_MASK), start=13):
        burst[offset] = (burst[offset] & (~mask & 0xFF)) | value


def _add_slot_type(burst: bytearray, data_type: int) -> None:
    slot_type = _golay_20_8_7((_COLOR_CODE << 4) | data_type)
    first, second, third = slot_type
    burst[12] = (burst[12] & 0xC0) | ((first >> 2) & 0x3F)
    burst[13] = (
        (burst[13] & 0x0F)
        | ((first << 6) & 0xC0)
        | ((second >> 2) & 0x30)
    )
    burst[19] = (burst[19] & 0xF0) | ((second >> 2) & 0x0F)
    burst[20] = (
        (burst[20] & 0x03)
        | ((second << 6) & 0xC0)
        | ((third >> 2) & 0x3C)
    )


def _golay_20_8_7(value: int) -> bytes:
    pattern = value << 11
    auxiliary = 0x40000
    while pattern & 0xFFFFF800:
        while not auxiliary & pattern:
            auxiliary >>= 1
        pattern ^= (auxiliary // 0x800) * 0x0C75

    code_without_extension = (value << 11) | pattern
    extension = code_without_extension.bit_count() & 1
    return bytes(
        (
            value,
            pattern >> 3,
            ((pattern & 0x07) << 5) | (extension << 4),
        )
    )


def _rs129_parity(message: bytes) -> tuple[int, int, int]:
    parity = [0, 0, 0]
    for value in message:
        feedback = value ^ parity[2]
        parity[2] = parity[1] ^ _gf256_multiply(14, feedback)
        parity[1] = parity[0] ^ _gf256_multiply(56, feedback)
        parity[0] = _gf256_multiply(64, feedback)
    return parity[0], parity[1], parity[2]


def _gf256_multiply(left: int, right: int) -> int:
    result = 0
    while right:
        if right & 1:
            result ^= left
        right >>= 1
        left <<= 1
        if left & 0x100:
            left ^= 0x11D
    return result


def _encode_bptc_196_96(data: bytes, burst: bytearray) -> None:
    input_bits = _bytes_to_bits(data)
    deinterleaved = [False] * 196
    position = 0
    for start, end in (
        (4, 11),
        (16, 26),
        (31, 41),
        (46, 56),
        (61, 71),
        (76, 86),
        (91, 101),
        (106, 116),
        (121, 131),
    ):
        for index in range(start, end + 1):
            deinterleaved[index] = input_bits[position]
            position += 1

    for row in range(9):
        _hamming_15_11_3(deinterleaved, row * 15 + 1)

    for column in range(15):
        values = [deinterleaved[column + 1 + row * 15] for row in range(13)]
        _hamming_13_9_3(values)
        for row, value in enumerate(values):
            deinterleaved[column + 1 + row * 15] = value

    raw = [False] * 196
    for index, value in enumerate(deinterleaved):
        raw[(index * 181) % 196] = value

    packed = _bits_to_bytes(raw[:96])
    burst[:12] = packed
    bridge = _bits_to_bytes(raw[96:104])[0]
    burst[12] = (burst[12] & 0x3F) | (bridge & 0xC0)
    burst[20] = (burst[20] & 0xFC) | ((bridge >> 4) & 0x03)
    burst[21:33] = _bits_to_bytes(raw[100:196])


def _hamming_15_11_3(bits: list[bool], offset: int) -> None:
    data = bits[offset : offset + 15]
    data[11] = data[0] ^ data[1] ^ data[2] ^ data[3] ^ data[5] ^ data[7] ^ data[8]
    data[12] = data[1] ^ data[2] ^ data[3] ^ data[4] ^ data[6] ^ data[8] ^ data[9]
    data[13] = data[2] ^ data[3] ^ data[4] ^ data[5] ^ data[7] ^ data[9] ^ data[10]
    data[14] = data[0] ^ data[1] ^ data[2] ^ data[4] ^ data[6] ^ data[7] ^ data[10]
    bits[offset : offset + 15] = data


def _hamming_13_9_3(data: list[bool]) -> None:
    data[9] = data[0] ^ data[1] ^ data[3] ^ data[5] ^ data[6]
    data[10] = data[0] ^ data[1] ^ data[2] ^ data[4] ^ data[6] ^ data[7]
    data[11] = data[0] ^ data[1] ^ data[2] ^ data[3] ^ data[5] ^ data[7] ^ data[8]
    data[12] = data[0] ^ data[2] ^ data[4] ^ data[5] ^ data[8]


def _encode_embedded_lc(link_control: bytes) -> tuple[bool, ...]:
    link_bits = _bytes_to_bits(link_control)
    crc = sum(link_control) % 31
    matrix = [False] * 128
    for bit, index in zip(
        (crc & (1 << shift) != 0 for shift in range(5)),
        (106, 90, 74, 58, 42),
    ):
        matrix[index] = bit

    source_position = 0
    for start, end in (
        (0, 10),
        (16, 26),
        (32, 41),
        (48, 57),
        (64, 73),
        (80, 89),
        (96, 105),
    ):
        for index in range(start, end + 1):
            matrix[index] = link_bits[source_position]
            source_position += 1

    for row in range(7):
        _hamming_16_11_4(matrix, row * 16)
    for column in range(16):
        matrix[column + 112] = (
            matrix[column]
            ^ matrix[column + 16]
            ^ matrix[column + 32]
            ^ matrix[column + 48]
            ^ matrix[column + 64]
            ^ matrix[column + 80]
            ^ matrix[column + 96]
        )

    raw = [False] * 128
    position = 0
    for index in range(128):
        raw[index] = matrix[position]
        position += 16
        if position > 127:
            position -= 127
    return tuple(raw)


def _hamming_16_11_4(bits: list[bool], offset: int) -> None:
    data = bits[offset : offset + 16]
    data[11] = data[0] ^ data[1] ^ data[2] ^ data[3] ^ data[5] ^ data[7] ^ data[8]
    data[12] = data[1] ^ data[2] ^ data[3] ^ data[4] ^ data[6] ^ data[8] ^ data[9]
    data[13] = data[2] ^ data[3] ^ data[4] ^ data[5] ^ data[7] ^ data[9] ^ data[10]
    data[14] = data[0] ^ data[1] ^ data[2] ^ data[4] ^ data[6] ^ data[7] ^ data[10]
    data[15] = data[0] ^ data[2] ^ data[5] ^ data[6] ^ data[8] ^ data[9] ^ data[10]
    bits[offset : offset + 16] = data


def _bytes_to_bits(data: bytes) -> list[bool]:
    return [
        bool(value & (0x80 >> shift))
        for value in data
        for shift in range(8)
    ]


def _bits_to_bytes(bits: tuple[bool, ...] | list[bool]) -> bytes:
    if len(bits) % 8:
        raise ValueError("Die Bitanzahl muss durch 8 teilbar sein.")
    return bytes(
        sum((0x80 >> shift) for shift, bit in enumerate(bits[offset : offset + 8]) if bit)
        for offset in range(0, len(bits), 8)
    )
