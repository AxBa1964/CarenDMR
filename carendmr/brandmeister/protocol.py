"""Paketbildung für den von DroidStar verwendeten DMR-Master-Handshake."""

from __future__ import annotations

import hashlib
from enum import Enum, auto


class LoginState(Enum):
    DISCONNECTED = auto()
    WAITING_LOGIN_ACK = auto()
    WAITING_AUTH_ACK = auto()
    WAITING_CONFIG_ACK = auto()
    CONNECTED = auto()
    REJECTED = auto()


def _id_bytes(dmr_id: int) -> bytes:
    if not 1 <= dmr_id <= 0xFFFFFFFF:
        raise ValueError("Die DMR-ID liegt außerhalb des 32-Bit-Bereichs.")
    return dmr_id.to_bytes(4, byteorder="big", signed=False)


def build_login_packet(dmr_id: int) -> bytes:
    return b"RPTL" + _id_bytes(dmr_id)


def build_auth_packet(dmr_id: int, challenge: bytes, password: str) -> bytes:
    if len(challenge) != 4:
        raise ValueError("Die Master-Challenge muss genau vier Bytes lang sein.")
    if not password:
        raise ValueError("Das BrandMeister-Hotspot-Passwort fehlt.")
    digest = hashlib.sha256(challenge + password.encode("utf-8")).digest()
    return b"RPTK" + _id_bytes(dmr_id) + digest


def _ascii_field(value: str, width: int, *, left: bool = True) -> bytes:
    encoded = value.encode("ascii", errors="replace")[:width]
    return encoded.ljust(width, b" ") if left else encoded.rjust(width, b"0")


def build_config_packet(
    *,
    dmr_id: int,
    callsign: str,
    frequency_hz: int,
    latitude: float,
    longitude: float,
    location: str,
    description: str,
    url: str,
    software_id: str,
    package_id: str,
) -> bytes:
    """Erzeugt das 302-Byte-RPTC-Paket entsprechend DroidStar."""
    callsign = callsign.strip().upper()
    if not callsign or len(callsign) > 8:
        raise ValueError("Das Rufzeichen muss 1 bis 8 Zeichen lang sein.")
    if not 0 <= frequency_hz <= 999_999_999:
        raise ValueError("Die Frequenz muss in neun Dezimalstellen passen.")

    # DroidStar uses sprintf("%08f") / sprintf("%09f") with the
    # default six decimal places and then copies exactly 8/9 bytes.
    latitude_text = f"{latitude:08f}"[:8]
    longitude_text = f"{longitude:09f}"[:9]

    body = b"".join([
        _ascii_field(callsign, 8),
        _ascii_field(str(frequency_hz), 9, left=False),
        _ascii_field(str(frequency_hz), 9, left=False),
        b"01",
        b"01",
        _ascii_field(latitude_text, 8),
        _ascii_field(longitude_text, 9),
        b"000",
        _ascii_field(location, 20),
        _ascii_field(description, 19),
        b"4",
        _ascii_field(url, 124),
        _ascii_field(software_id, 40),
        _ascii_field(package_id, 40),
    ])
    packet = b"RPTC" + _id_bytes(dmr_id) + body
    if len(packet) != 302:
        raise AssertionError(
            f"Internes Formatproblem: RPTC hat {len(packet)} statt 302 Bytes."
        )
    return packet


def build_options_packet(dmr_id: int, options: str) -> bytes:
    """Erzeugt das optionale RPTO-Paket wie DroidStar.

    BrandMeister nutzt diese Optionen unter anderem, um statische
    Talkgroups für die Sitzung zu abonnieren.
    """
    text = str(options).strip()
    if not text:
        raise ValueError("Die BrandMeister-Optionen dürfen nicht leer sein.")
    encoded = text.encode("ascii", errors="strict")
    return b"RPTO" + _id_bytes(dmr_id) + encoded


def build_ping_packet(dmr_id: int) -> bytes:
    return b"RPTPING" + _id_bytes(dmr_id)


def build_close_packet(dmr_id: int) -> bytes:
    return b"RPTCL" + _id_bytes(dmr_id)


def is_master_ack(packet: bytes) -> bool:
    return packet.startswith(b"RPTACK") and len(packet) >= 6


def is_master_nak(packet: bytes) -> bool:
    return packet.startswith(b"MSTNAK")


def is_master_pong(packet: bytes, dmr_id: int | None = None) -> bool:
    if not packet.startswith(b"MSTPONG"):
        return False
    if dmr_id is None:
        return len(packet) == 11
    return packet == b"MSTPONG" + _id_bytes(dmr_id)


def extract_challenge(packet: bytes) -> bytes:
    if not is_master_ack(packet) or len(packet) < 10:
        raise ValueError(
            "Die erste Master-Antwort enthält keine vier Byte große Challenge."
        )
    return packet[6:10]
