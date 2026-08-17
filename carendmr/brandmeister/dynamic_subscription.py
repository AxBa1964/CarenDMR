"""Dynamische BrandMeister-Talkgroup-Aktivierung ohne HTTP-API."""

from __future__ import annotations

import secrets
import time
from typing import Callable

from .dmrd import DmrdCallType
from .silent_call import build_silent_call_fixture


def validate_receive_target(talkgroup: int, timeslot: int) -> tuple[int, int]:
    if not isinstance(talkgroup, int) or isinstance(talkgroup, bool):
        raise TypeError("Die Talkgroup muss eine ganze Zahl sein.")
    if not 1 <= talkgroup <= 0xFFFFFF:
        raise ValueError("Die Talkgroup muss zwischen 1 und 16777215 liegen.")
    if timeslot not in (1, 2):
        raise ValueError("Der Timeslot muss 1 oder 2 sein.")
    return talkgroup, timeslot


def normalize_call_type(call_type: str) -> str:
    normalized = str(call_type).strip().lower()
    if normalized not in {"group", "private"}:
        raise ValueError("Die Rufart muss 'group' oder 'private' sein.")
    return normalized


def build_dynamic_tg_packets(*, dmr_id: int, talkgroup: int, timeslot: int,
                             stream_id: int | None = None, call_type: str = "group") -> tuple[bytes, ...]:
    """Erzeugt einen vollständigen gültigen stummen DMR-Gruppenruf."""
    talkgroup, timeslot = validate_receive_target(talkgroup, timeslot)
    call_type = normalize_call_type(call_type)
    if call_type != "group":
        raise ValueError("Dynamische Talkgroup-Aktivierung ist nur für Gruppenrufe zulässig.")
    if not 1 <= dmr_id <= 0xFFFFFF:
        raise ValueError("Die DMR-ID muss für DMRD in 24 Bit passen.")
    if stream_id is None:
        stream_id = secrets.randbelow(0xFFFFFFFF) + 1
    return build_silent_call_fixture(
        source_id=dmr_id, repeater_id=dmr_id, destination_id=talkgroup,
        timeslot=timeslot, stream_id=stream_id,
        call_type=DmrdCallType.GROUP,
    ).to_bytes()


def activate_dynamic_talkgroup(transport, *, dmr_id: int, talkgroup: int,
                               timeslot: int, call_type: str = "group", pause_seconds: float = 0.06,
                               sleep: Callable[[float], None] = time.sleep) -> None:
    """Sendet einen vollständigen stummen Gruppenruf über die Login-Sitzung.

    Privatrufe dürfen diesen Mechanismus nicht verwenden: Der vermeintliche
    Aktivierungsruf wäre bereits ein echter privater DMR-Ruf.
    """
    packets = build_dynamic_tg_packets(
        dmr_id=dmr_id, talkgroup=talkgroup, timeslot=timeslot, call_type=call_type
    )
    for index, packet in enumerate(packets):
        sent = transport.send(packet)
        if sent is not None and sent != len(packet):
            raise RuntimeError("DMRD-Aktivierungspaket wurde nicht vollständig gesendet.")
        if index + 1 < len(packets):
            sleep(pause_seconds)
