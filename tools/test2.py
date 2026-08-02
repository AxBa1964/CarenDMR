"""CarenDMR - Vollständiger DMR-Empfänger mit zweifacher TG-Umschaltung.

Sendet bei Umschaltung sowohl ein DMRD-UDP-Signal als auch einen API-Call,
damit der BrandMeister-Master den Stream garantiert an die PC-IP routed.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import platform
import socket
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

try:
    import numpy as np
    import requests
    import sounddevice as sd
except ImportError as exc:
    raise SystemExit(
        "Fehlende Abhängigkeiten. Bitte ausführen:\n"
        "python -m pip install numpy sounddevice requests"
    ) from exc


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "brandmeister.local.json"

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
    api_key: str


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
        description=str(data.get("description", "CarenDMR receiver")),
        url=str(data.get("url", "")),
        software_id=str(data.get("software_id", "20181107_Pi-Star")),
        package_id=str(data.get("package_id", "MMDVM_MMDVM_HS_Hat")),
        api_key=str(data.get("api_key", "")),
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
    sock.send(packet)
    answer = recv_packet(sock, "RPTACK")
    expect_ack(answer, "RPTL")
    challenge = answer[6:10]

    digest = hashlib.sha256(challenge + config.password.encode("utf-8")).digest()
    packet = b"RPTK" + dmr_id + digest
    sock.send(packet)
    expect_ack(recv_packet(sock, "RPTACK"), "RPTK")

    packet = build_rptc(config)
    sock.send(packet)
    expect_ack(recv_packet(sock, "RPTACK"), "RPTC")
    print("BrandMeister-Anmeldung erfolgreich.")


def switch_talkgroup_api(api_key: str, dmr_id: int, timeslot: int, target_tg: int) -> bool:
    if not api_key:
        return False

    url = f"https://api.brandmeister.network/v2/device/{dmr_id}/talkgroup"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "slot": timeslot,
        "group": target_tg,
    }

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=3.0)
        return res.status_code in (200, 201)
    except Exception:
        return False


def trigger_udp_subscription(sock: socket.socket, config: Config, target_tg: int, timeslot: int) -> None:
    """Schickt direkte UDP DMRD-Signalpakete für TS1 und TS2, um den Server zum Streamen zu zwingen."""
    src_bytes = id_bytes(config.dmr_id)[1:]
    dst_bytes = id_bytes(target_tg)[1:]
    repeater_id = id_bytes(config.dmr_id)
    stream_id = b"\x11\x22\x33\x44"

    # DMR Header-Frame mit Sync für Voice
    sync_bs = b"\x75\x5d\x7f\x77\x5d\x75"
    payload = (b"\x00" + dst_bytes + src_bytes).ljust(12, b"\x00") + sync_bs + b"\x00" * 12

    for slot in (1, 2):
        slot_flag = 0x80 if slot == 2 else 0x00
        flags = bytes([slot_flag])
        
        # Header (seq=0) & Terminator (seq=15)
        pkt_hdr = b"DMRD\x00" + src_bytes + dst_bytes + repeater_id + flags + stream_id + payload
        pkt_end = b"DMRD\x0f" + src_bytes + dst_bytes + repeater_id + flags + stream_id + payload
        
        sock.send(pkt_hdr)
        time.sleep(0.02)
        sock.send(pkt_end)
        time.sleep(0.02)


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
            raise RuntimeError(f"Decoder DLL fehlt: {path}")
        self.lib = ctypes.CDLL(str(path))
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

    def decode(self, codeword: bytes) -> np.ndarray:
        encoded = (ctypes.c_uint8 * AMBE_BYTES).from_buffer_copy(codeword)
        samples = (ctypes.c_int16 * PCM_SAMPLES)()
        errors = ctypes.c_int(0)
        self.lib.carendmr_mbe_decode(self.handle, encoded, samples, ctypes.byref(errors))
        return np.ctypeslib.as_array(samples).copy()

    def close(self) -> None:
        if getattr(self, "handle", None):
            self.lib.carendmr_mbe_decoder_destroy(self.handle)


def parse_u24(data: bytes) -> int:
    return int.from_bytes(data, "big", signed=False)


def extract_ambe(payload: bytes) -> tuple[bytes, bytes, bytes]:
    packed = bytearray(payload[:14])
    packed[13] = (packed[13] & 0xF0) | (payload[19] & 0x0F)
    packed.extend(payload[20:33])
    return bytes(packed[0:9]), bytes(packed[9:18]), bytes(packed[18:27])


class ReceiverState:
    def __init__(self, initial_tg: int = 262) -> None:
        self.target_tg = initial_tg
        self.lock = threading.Lock()

    def update(self, tg: int) -> None:
        with self.lock:
            self.target_tg = tg

    def check_match(self, destination: int) -> bool:
        with self.lock:
            return destination == self.target_tg


def input_thread_func(sock: socket.socket, config: Config, state: ReceiverState) -> None:
    time.sleep(1.0)
    print("\n------------------------------------------------------------")
    print(" CarenDMR EMPFÄNGER BEREIT:")
    print(" Tippe eine TG ein (z. B. '262' oder '91') und drücke ENTER.")
    print("------------------------------------------------------------\n")

    while True:
        try:
            user_input = input().strip()
            if not user_input:
                continue

            tg = int(user_input.split(":")[0])
            print(f"\n[STEUERUNG] Aktiviere Stream für TG {tg}...")

            # 1. API Triggern für TS1 und TS2
            switch_talkgroup_api(config.api_key, config.dmr_id, 1, tg)
            switch_talkgroup_api(config.api_key, config.dmr_id, 2, tg)

            # 2. UDP Voice-Touch triggern (wie PTT-Antritt)
            trigger_udp_subscription(sock, config, tg, 1)

            state.update(tg)
            print(f">>> TG {tg} aktiviert! Warte auf Sprachdaten... <<<\n")

        except ValueError:
            print("[CLI] Bitte eine Zahl eingeben (z. B. 262).")
        except (EOFError, KeyboardInterrupt):
            break


def run() -> int:
    config = load_config()
    state = ReceiverState(initial_tg=262)

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

    started = time.monotonic()
    next_ping = started + HEARTBEAT_SECONDS

    try:
        login(sock, config)
        stream.start()

        # Initialer Trigger für TG 262
        trigger_udp_subscription(sock, config, 262, 1)

        cli_thread = threading.Thread(
            target=input_thread_func, args=(sock, config, state), daemon=True
        )
        cli_thread.start()

        print("Empfänger läuft! Warte auf Pakete...\n")

        while True:
            now = time.monotonic()
            if now >= next_ping:
                sock.send(b"RPTPING" + id_bytes(config.dmr_id))
                next_ping = now + HEARTBEAT_SECONDS

            try:
                packet = sock.recv(2048)
            except socket.timeout:
                continue

            if packet.startswith(b"MSTPONG"):
                continue

            if not packet.startswith(b"DMRD") or len(packet) != 55:
                continue

            flags = packet[15]
            src = parse_u24(packet[5:8])
            dst = parse_u24(packet[8:11])
            ts = 2 if flags & 0x80 else 1

            # Prüfe ob Paket zu eurer gewählten TG passt
            if not state.check_match(dst):
                continue

            print(f"AUDIO RX -> Call von {src} auf TG {dst} (Slot {ts})")

            payload = packet[20:53]
            for word in extract_ambe(payload):
                try:
                    pcm = decoder.decode(word)
                    stream.write(pcm.tobytes())
                except Exception as exc:
                    print(f"Decoder-Error: {exc}")

    except KeyboardInterrupt:
        print("\nBeendet.")
    finally:
        stream.close()
        decoder.close()
        sock.close()

    return 0


if __name__ == "__main__":
    sys.exit(run())