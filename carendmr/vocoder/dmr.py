"""Extraction of the three AMBE+2 codewords carried by a DMR voice burst."""

from __future__ import annotations

from carendmr.brandmeister.dmrd import (
    DMRD_PAYLOAD_SIZE,
    DmrdFrameClass,
    DmrdPacket,
)


def extract_ambe_codewords(packet: DmrdPacket) -> tuple[bytes, bytes, bytes]:
    """Return the three 9-byte AMBE codewords from a validated voice packet."""

    if packet.frame_class not in (DmrdFrameClass.VOICE, DmrdFrameClass.VOICE_SYNC):
        raise ValueError("Nur DMR-Sprachrahmen enthalten AMBE-Codewörter.")
    payload = packet.payload
    if len(payload) != DMRD_PAYLOAD_SIZE:
        raise AssertionError("Das validierte DMRD-Modell enthält falsche Nutzdaten.")

    packed = bytearray(payload[:14])
    packed[13] = (packed[13] & 0xF0) | (payload[19] & 0x0F)
    packed.extend(payload[20:33])
    if len(packed) != 27:
        raise AssertionError("Internes AMBE-Extraktionsproblem.")
    return bytes(packed[:9]), bytes(packed[9:18]), bytes(packed[18:27])
