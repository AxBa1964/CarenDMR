"""Minimaler, unabhaengiger BrandMeister-TG91-Referenzempfaenger.

Absicht:
- keine Imports aus dem Paket ``carendmr``
- eigener UDP-Socket und eigener Homebrew-Handshake
- eigener DMRD-Parser und eigene AMBE-Extraktion
- direkter Aufruf des nativen mbelib-Decoders per ctypes
- direkte PCM-Ausgabe ueber sounddevice

Das Programm sendet keine DMRD-Sprachpakete. Es meldet sich nur an, haelt die
Sitzung mit RPTPING offen und gibt empfangenen Gruppenverkehr fuer TG91/TS2 aus.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import platform
import socket
import sys
import time
from dataclasses import dataclass
from pathlib import Path

try:
    import numpy as np
    import sounddevice as sd
except ImportError as exc:
    raise SystemExit(
        "Fehlende Abhaengigkeit. Bitte ausfuehren: "
        "python -m pip install numpy sounddevice"
    ) from exc


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "brandmeister.local.json"
TARGET_TG = 91
TARGET_TS = 2
SAMPLE_RATE = 8000
HEARTBEAT_SECONDS = 5.0
SOCKET_TIMEOUT_SECONDS = 1.0
AMBE_BYTES = 9
PCM_SAMPLES = 160


@dataclass(frozen=True)
class Config:
    host: str
    port: int
    dmr_id: int
    password: str
    callsign: str
    frequency_hz: int
    latitude: float
    longitude: float
    location: str
    description: str
    url: str
    software_id: str
    package_id: str


def load_config() -> Config:
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return Config(
        host=str(data["host"]),
        port=int(data.get("port", 62031)),
        dmr_id=int(data["dmr_id"]),
        password=str(data["password"]),
        callsign=str(data["callsign"]).strip().upper(),
        frequency_hz=int(data.get("frequency_hz", 438_800_000)),
        latitude=float(data.get("latitude", 0.0)),
        longitude=float(data.get("longitude", 0.0)),
        location=str(data.get("location", "")),
        description=str(data.get("description", "CarenDMR reference receiver")),
        url=str(data.get("url", "")),
        software_id=str(data.get("software_id", "20181107_Pi-Star")),
        package_id=str(data.get("package_id", "MMDVM_MMDVM_HS_Hat")),
    )


def id_bytes(value: int) -> bytes:
    return int(value).to_bytes(4, "big", signed=False)


def ascii_field(value: str, width: int, *, zero_pad: bool = False) -> bytes:
    raw = value.encode("ascii", errors="replace")[:width]
    return raw.rjust(width, b"0") if zero_pad else raw.ljust(width, b" ")


def build_rptc(config: Config) -> bytes:
    latitude = f"{config.latitude:08f}"[:8]
    longitude = f"{config.longitude:09f}"[:9]
    body = b"".join(
        (
            ascii_field(config.callsign, 8),
            ascii_field(str(config.frequency_hz), 9, zero_pad=True),
            ascii_field(str(config.frequency_hz), 9, zero_pad=True),
            b"01",
            b"01",
            ascii_field(latitude, 8),
            ascii_field(longitude, 9),
            b"000",
            ascii_field(config.location, 20),
            ascii_field(config.description, 19),
            b"4",
            ascii_field(config.url, 124),
            ascii_field(config.software_id, 40),
            ascii_field(config.package_id, 40),
        )
    )
    packet = b"RPTC" + id_bytes(config.dmr_id) + body
    if len(packet) != 302:
        raise RuntimeError(f"RPTC hat {len(packet)} statt 302 Bytes")
    return packet


def recv_packet(sock: socket.socket, label: str) -> bytes:
    packet = sock.recv(2048)
    print(f"RX {label:<8} {packet[:12]!r} ({len(packet)} Byte)")
    return packet


def expect_ack(packet: bytes, step: str) -> None:
    if packet.startswith(b"MSTNAK"):
        raise RuntimeError(f"BrandMeister lehnt {step} mit MSTNAK ab")
    if not packet.startswith(b"RPTACK"):
        raise RuntimeError(f"Unerwartete Antwort auf {step}: {packet[:20]!r}")


def login(sock: socket.socket, config: Config) -> None:
    dmr_id = id_bytes(config.dmr_id)

    packet = b"RPTL" + dmr_id
    print(f"TX RPTL     ({len(packet)} Byte)")
    sock.send(packet)
    answer = recv_packet(sock, "RPTACK")
    expect_ack(answer, "RPTL")
    if len(answer) < 10:
        raise RuntimeError("RPTACK enthaelt keine vier Byte grosse Challenge")
    challenge = answer[6:10]

    digest = hashlib.sha256(challenge + config.password.encode("utf-8")).digest()
    packet = b"RPTK" + dmr_id + digest
    print(f"TX RPTK     ({len(packet)} Byte)")
    sock.send(packet)
    expect_ack(recv_packet(sock, "RPTACK"), "RPTK")

    packet = build_rptc(config)
    print(f"TX RPTC     ({len(packet)} Byte)")
    sock.send(packet)
    expect_ack(recv_packet(sock, "RPTACK"), "RPTC")
    print("BrandMeister-Anmeldung erfolgreich. Warte auf TG91/TS2.")


def library_path() -> Path:
    system = platform.system()
    if system == "Windows":
        name = "carendmr_mbe.dll"
    elif system == "Darwin":
        name = "libcarendmr_mbe.dylib"
    else:
        name = "libcarendmr_mbe.so"
    return PROJECT_ROOT / "native" / name


class NativeDecoder:
    def __init__(self) -> None:
        path = library_path()
        if not path.exists():
            raise RuntimeError(
                f"Nativer Decoder fehlt: {path}\n"
                "Unter Windows zuerst ausfuehren: .\\native\\build_windows.ps1"
            )
        try:
            self.lib = ctypes.CDLL(str(path))
        except OSError as exc:
            raise RuntimeError(f"Decoder-DLL konnte nicht geladen werden: {exc}") from exc

        byte_p = ctypes.POINTER(ctypes.c_uint8)
        sample_p = ctypes.POINTER(ctypes.c_int16)
        self.lib.carendmr_mbe_decoder_create.restype = ctypes.c_void_p
        self.lib.carendmr_mbe_decoder_destroy.argtypes = [ctypes.c_void_p]
        self.lib.carendmr_mbe_decode.argtypes = [
            ctypes.c_void_p,
            byte_p,
            sample_p,
            ctypes.POINTER(ctypes.c_int),
        ]
        self.lib.carendmr_mbe_decode.restype = ctypes.c_int
        self.handle = self.lib.carendmr_mbe_decoder_create()
        if not self.handle:
            raise RuntimeError("Nativer Decoder konnte nicht initialisiert werden")

    def decode(self, codeword: bytes) -> np.ndarray:
        encoded = (ctypes.c_uint8 * AMBE_BYTES).from_buffer_copy(codeword)
        samples = (ctypes.c_int16 * PCM_SAMPLES)()
        errors = ctypes.c_int(0)
        result = self.lib.carendmr_mbe_decode(
            self.handle, encoded, samples, ctypes.byref(errors)
        )
        if result != 0:
            raise RuntimeError(f"Decoderfehler {result}")
        return np.ctypeslib.as_array(samples).copy()

    def close(self) -> None:
        if getattr(self, "handle", None):
            self.lib.carendmr_mbe_decoder_destroy(self.handle)
            self.handle = None


def parse_u24(data: bytes) -> int:
    return int.from_bytes(data, "big", signed=False)


def extract_ambe(payload: bytes) -> tuple[bytes, bytes, bytes]:
    if len(payload) != 33:
        raise ValueError("DMRD-Nutzdaten muessen 33 Byte lang sein")
    packed = bytearray(payload[:14])
    packed[13] = (packed[13] & 0xF0) | (payload[19] & 0x0F)
    packed.extend(payload[20:33])
    return bytes(packed[0:9]), bytes(packed[9:18]), bytes(packed[18:27])


def is_target_voice(packet: bytes) -> tuple[bool, dict[str, int]]:
    if len(packet) != 55 or not packet.startswith(b"DMRD"):
        return False, {}
    flags = packet[15]
    source = parse_u24(packet[5:8])
    destination = parse_u24(packet[8:11])
    timeslot = 2 if flags & 0x80 else 1
    private_call = bool(flags & 0x40)
    data_sync = bool(flags & 0x20)
    voice = not data_sync and ((flags & 0x0F) <= 5)
    details = {
        "sequence": packet[4],
        "source": source,
        "destination": destination,
        "timeslot": timeslot,
        "private": int(private_call),
        "flags": flags,
    }
    target = (
        destination == TARGET_TG
        and timeslot == TARGET_TS
        and not private_call
        and voice
    )
    return target, details


def run() -> int:
    config = load_config()
    endpoint = socket.getaddrinfo(
        config.host, config.port, socket.AF_UNSPEC, socket.SOCK_DGRAM
    )[0]
    family, socktype, proto, _, address = endpoint

    sock = socket.socket(family, socktype, proto)
    sock.settimeout(SOCKET_TIMEOUT_SECONDS)
    sock.connect(address)

    decoder = NativeDecoder()
    stream = sd.RawOutputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
        blocksize=0,
        latency="low",
    )

    datagrams = pongs = dmrd = target_bursts = codewords = pcm_samples = 0
    decode_errors = 0
    started = time.monotonic()
    next_ping = started + HEARTBEAT_SECONDS

    try:
        login(sock, config)
        stream.start()
        print("Audioausgabe gestartet. Abbruch mit Strg+C.\n")

        while True:
            now = time.monotonic()
            if now >= next_ping:
                ping = b"RPTPING" + id_bytes(config.dmr_id)
                sock.send(ping)
                print("TX RPTPING")
                next_ping = now + HEARTBEAT_SECONDS

            try:
                packet = sock.recv(2048)
            except socket.timeout:
                continue

            datagrams += 1
            if packet.startswith(b"MSTPONG"):
                pongs += 1
                continue
            if not packet.startswith(b"DMRD"):
                print(f"RX {packet[:12]!r} ({len(packet)} Byte)")
                continue

            dmrd += 1
            target, info = is_target_voice(packet)
            print(
                "RX DMRD "
                f"seq={info.get('sequence')} src={info.get('source')} "
                f"dst={info.get('destination')} ts={info.get('timeslot')} "
                f"private={info.get('private')} flags=0x{info.get('flags', 0):02X}"
            )
            if not target:
                continue

            target_bursts += 1
            payload = packet[20:53]
            for word in extract_ambe(payload):
                try:
                    pcm = decoder.decode(word)
                except Exception as exc:
                    decode_errors += 1
                    print(f"Decoderfehler: {exc}")
                    continue
                stream.write(pcm.tobytes())
                codewords += 1
                pcm_samples += len(pcm)

    except KeyboardInterrupt:
        print("\nAbbruch angefordert.")
    finally:
        try:
            sock.send(b"RPTCL" + id_bytes(config.dmr_id))
        except OSError:
            pass
        stream.stop()
        stream.close()
        decoder.close()
        sock.close()

    print("\nStatistik")
    print(f"Laufzeit:              {time.monotonic() - started:.1f} s")
    print(f"Datagramme:            {datagrams}")
    print(f"MSTPONG:               {pongs}")
    print(f"DMRD gesamt:           {dmrd}")
    print(f"TG91/TS2-Sprachbursts: {target_bursts}")
    print(f"AMBE-Codewoerter:      {codewords}")
    print(f"PCM-Samples:           {pcm_samples}")
    print(f"Decoderfehler:         {decode_errors}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except Exception as exc:
        print(f"FEHLER: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
