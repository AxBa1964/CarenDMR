"""Qt-unabhängiges Protokoll für die lokale Kanalübergabe."""
from __future__ import annotations

import json

from carendmr.domain import DmrChannel

MAX_MESSAGE_BYTES = 4096


def decode_request(raw: bytes) -> DmrChannel:
    if len(raw) > MAX_MESSAGE_BYTES:
        raise ValueError("IPC-Nachricht ist zu groß.")
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict) or payload.get("command") != "set_channel":
        raise ValueError("Unbekannter IPC-Befehl.")
    target = int(payload.get("target", 0))
    timeslot = int(payload.get("timeslot", 2))
    call_type = str(payload.get("call_type", "group")).strip().lower()
    name = str(payload.get("name", "")).strip()
    return DmrChannel(target, timeslot, call_type, name=name).normalized()


def encode_request(channel: DmrChannel) -> bytes:
    normalized = channel.normalized()
    payload = {
        "command": "set_channel",
        "target": normalized.target,
        "timeslot": normalized.timeslot,
        "call_type": normalized.call_type,
        "name": normalized.name,
    }
    return (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
