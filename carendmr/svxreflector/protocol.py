"""SvxReflector-Netzprotokoll, Version 2.0 (reine Kodierung, ohne Netzwerk).

TCP: Jeder Rahmen beginnt mit einer 32-Bit-Länge (Big Endian), danach folgt
die Nachricht: 16-Bit-Typ und die Felder. Zeichenketten und Byte-Listen haben
eine 16-Bit-Länge vorweg, Listen eine 16-Bit-Anzahl.

UDP (Version < 3): Kopf aus Typ, Client-ID und Folgenummer (je 16 Bit),
danach die Felder. Sprache: ``MsgUdpAudio`` mit Opus-Daten.

Feldreihenfolgen nach SvxLink ``ReflectorMsg.h`` (``ASYNC_MSG_MEMBERS``).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import struct
from dataclasses import dataclass, field

PROTO_MAJOR = 2
PROTO_MINOR = 0

MAX_FRAME_SIZE = 32768  # MAX_POSTAUTH_FRAME_SIZE im Server

# TCP-Nachrichtentypen
MSG_HEARTBEAT = 1
MSG_PROTO_VER = 5
MSG_PROTO_VER_DOWNGRADE = 6
MSG_AUTH_CHALLENGE = 10
MSG_AUTH_RESPONSE = 11
MSG_AUTH_OK = 12
MSG_ERROR = 13
MSG_SERVER_INFO = 100
MSG_NODE_LIST = 101
MSG_NODE_JOINED = 102
MSG_NODE_LEFT = 103
MSG_TALKER_START = 104
MSG_TALKER_STOP = 105
MSG_SELECT_TG = 106
MSG_TG_MONITOR = 107
MSG_REQUEST_QSY = 109
MSG_NODE_INFO = 111

# UDP-Nachrichtentypen
UDP_HEARTBEAT = 1
UDP_AUDIO = 101
UDP_FLUSH_SAMPLES = 102
UDP_ALL_SAMPLES_FLUSHED = 103

# Takt laut SvxLink ReflectorLogic.h (Zähler laufen im Sekundentakt).
TCP_HEARTBEAT_INTERVAL_SECONDS = 10.0
TCP_HEARTBEAT_TIMEOUT_SECONDS = 15.0
UDP_HEARTBEAT_INTERVAL_SECONDS = 15.0

# Opus-Audio im FM-Funknetz (SvxLink intern 16 kHz, 20-ms-Rahmen).
AUDIO_SAMPLE_RATE = 16000
AUDIO_FRAME_SAMPLES = 320


class ProtocolError(ValueError):
    """Eine Nachricht ist unvollständig oder ungültig."""


# ---------------------------------------------------------------- Bausteine

class _Reader:
    def __init__(self, data: bytes) -> None:
        self._data = data
        self._pos = 0

    def u8(self) -> int:
        return self._take(1)[0]

    def u16(self) -> int:
        return struct.unpack(">H", self._take(2))[0]

    def u32(self) -> int:
        return struct.unpack(">I", self._take(4))[0]

    def raw(self, count: int) -> bytes:
        return self._take(count)

    def bytes16(self) -> bytes:
        return self._take(self.u16())

    def text(self) -> str:
        return self.bytes16().decode("utf-8", errors="replace")

    def texts(self) -> tuple[str, ...]:
        return tuple(self.text() for _ in range(self.u16()))

    def remaining(self) -> int:
        return len(self._data) - self._pos

    def _take(self, count: int) -> bytes:
        if count < 0 or self._pos + count > len(self._data):
            raise ProtocolError("Nachricht ist kürzer als erwartet.")
        chunk = self._data[self._pos:self._pos + count]
        self._pos += count
        return chunk


def _text(value: str) -> bytes:
    data = value.encode("utf-8")
    if len(data) > 0xFFFF:
        raise ProtocolError("Zeichenkette ist zu lang.")
    return struct.pack(">H", len(data)) + data


def _bytes16(value: bytes) -> bytes:
    if len(value) > 0xFFFF:
        raise ProtocolError("Datenblock ist zu lang.")
    return struct.pack(">H", len(value)) + value


# ------------------------------------------------------------------ TCP

def frame(message: bytes) -> bytes:
    """Setzt die 32-Bit-Länge vor eine Nachricht."""
    return struct.pack(">I", len(message)) + message


class FrameBuffer:
    """Zerlegt einen TCP-Datenstrom in einzelne Nachrichten."""

    def __init__(self, max_frame_size: int = MAX_FRAME_SIZE) -> None:
        self._buffer = bytearray()
        self._max = max_frame_size

    def feed(self, data: bytes) -> list[bytes]:
        self._buffer.extend(data)
        messages: list[bytes] = []
        while len(self._buffer) >= 4:
            size = struct.unpack(">I", self._buffer[:4])[0]
            if size > self._max:
                raise ProtocolError(f"Rahmen zu groß ({size} Byte).")
            if len(self._buffer) < 4 + size:
                break
            messages.append(bytes(self._buffer[4:4 + size]))
            del self._buffer[:4 + size]
        return messages


def encode_proto_ver(major: int = PROTO_MAJOR, minor: int = PROTO_MINOR) -> bytes:
    return struct.pack(">HHH", MSG_PROTO_VER, major, minor)


def encode_heartbeat() -> bytes:
    return struct.pack(">H", MSG_HEARTBEAT)


def auth_digest(auth_key: str, challenge: bytes) -> bytes:
    """HMAC-SHA1 über die Herausforderung, Schlüssel = Key im Klartext."""
    return hmac.new(auth_key.encode("utf-8"), challenge, hashlib.sha1).digest()


def encode_auth_response(callsign: str, auth_key: str, challenge: bytes) -> bytes:
    return (
        struct.pack(">H", MSG_AUTH_RESPONSE)
        + _text(callsign)
        + _bytes16(auth_digest(auth_key, challenge))
    )


def encode_select_tg(talkgroup: int) -> bytes:
    if not 0 <= talkgroup <= 0xFFFFFFFF:
        raise ProtocolError("Ungültige Talkgroup.")
    return struct.pack(">HI", MSG_SELECT_TG, talkgroup)


def encode_tg_monitor(talkgroups: tuple[int, ...] | list[int]) -> bytes:
    unique = sorted({int(tg) for tg in talkgroups if int(tg) > 0})
    return struct.pack(">HH", MSG_TG_MONITOR, len(unique)) + b"".join(
        struct.pack(">I", tg) for tg in unique
    )


def encode_node_info(info: dict) -> bytes:
    data = json.dumps(info, ensure_ascii=False, separators=(",", ":"))
    return struct.pack(">H", MSG_NODE_INFO) + _text(data)


@dataclass(frozen=True)
class ProtoVer:
    major: int
    minor: int


@dataclass(frozen=True)
class ProtoVerDowngrade:
    major: int
    minor: int


@dataclass(frozen=True)
class AuthChallenge:
    challenge: bytes


@dataclass(frozen=True)
class AuthOk:
    pass


@dataclass(frozen=True)
class ServerError:
    message: str


@dataclass(frozen=True)
class ServerInfo:
    client_id: int
    nodes: tuple[str, ...] = ()
    codecs: tuple[str, ...] = ()


@dataclass(frozen=True)
class NodeList:
    nodes: tuple[str, ...]


@dataclass(frozen=True)
class NodeJoined:
    callsign: str


@dataclass(frozen=True)
class NodeLeft:
    callsign: str


@dataclass(frozen=True)
class TalkerStart:
    talkgroup: int
    callsign: str


@dataclass(frozen=True)
class TalkerStop:
    talkgroup: int
    callsign: str


@dataclass(frozen=True)
class RequestQsy:
    talkgroup: int


@dataclass(frozen=True)
class Heartbeat:
    pass


@dataclass(frozen=True)
class UnknownMessage:
    msg_type: int
    payload: bytes = field(repr=False, default=b"")


def decode_message(message: bytes):
    """Wandelt eine TCP-Nachricht (ohne Längenfeld) in ein Objekt."""
    reader = _Reader(message)
    msg_type = reader.u16()
    if msg_type == MSG_HEARTBEAT:
        return Heartbeat()
    if msg_type == MSG_PROTO_VER:
        return ProtoVer(reader.u16(), reader.u16())
    if msg_type == MSG_PROTO_VER_DOWNGRADE:
        return ProtoVerDowngrade(reader.u16(), reader.u16())
    if msg_type == MSG_AUTH_CHALLENGE:
        return AuthChallenge(reader.bytes16())
    if msg_type == MSG_AUTH_OK:
        return AuthOk()
    if msg_type == MSG_ERROR:
        return ServerError(reader.text())
    if msg_type == MSG_SERVER_INFO:
        reader.u16()  # reserviert
        client_id = reader.u16()
        nodes = reader.texts() if reader.remaining() >= 2 else ()
        codecs = reader.texts() if reader.remaining() >= 2 else ()
        return ServerInfo(client_id, nodes, codecs)
    if msg_type == MSG_NODE_LIST:
        return NodeList(reader.texts())
    if msg_type == MSG_NODE_JOINED:
        return NodeJoined(reader.text())
    if msg_type == MSG_NODE_LEFT:
        return NodeLeft(reader.text())
    if msg_type in (MSG_TALKER_START, MSG_TALKER_STOP):
        cls = TalkerStart if msg_type == MSG_TALKER_START else TalkerStop
        # Protokoll 1 hatte keine Talkgroup: nur das Rufzeichen.
        if reader.remaining() >= 6:
            body = message[2:]
            tg = struct.unpack(">I", body[:4])[0]
            length = struct.unpack(">H", body[4:6])[0]
            if len(body) == 6 + length:
                return cls(tg, body[6:6 + length].decode("utf-8", errors="replace"))
        return cls(0, reader.text())
    if msg_type == MSG_REQUEST_QSY:
        return RequestQsy(reader.u32())
    return UnknownMessage(msg_type, message[2:])


# ------------------------------------------------------------------ UDP

@dataclass(frozen=True)
class UdpMessage:
    msg_type: int
    client_id: int
    sequence: int
    audio: bytes = b""


def encode_udp(msg_type: int, client_id: int, sequence: int, audio: bytes | None = None) -> bytes:
    data = struct.pack(">HHH", msg_type, client_id & 0xFFFF, sequence & 0xFFFF)
    if msg_type == UDP_AUDIO:
        data += _bytes16(audio or b"")
    return data


def decode_udp(datagram: bytes) -> UdpMessage:
    reader = _Reader(datagram)
    msg_type, client_id, sequence = reader.u16(), reader.u16(), reader.u16()
    audio = reader.bytes16() if msg_type == UDP_AUDIO else b""
    return UdpMessage(msg_type, client_id, sequence, audio)


def base_callsign(callsign: str) -> str:
    """Rufzeichen ohne Zusatz, z. B. ``DK7EE-APP`` → ``DK7EE`` (für QRZ)."""
    return callsign.strip().upper().split("-", 1)[0]
