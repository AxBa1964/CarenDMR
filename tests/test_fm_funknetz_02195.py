"""0.2.1.95: FM-Funknetz (SvxReflector 2.0) – Protokoll, Konfiguration, Empfang."""
from __future__ import annotations

import json
import math
import os
import socket
import struct
import threading
import time
from pathlib import Path

import pytest

from carendmr.app import _build_parser
from carendmr.svxreflector import protocol as p
from carendmr.svxreflector.client import (
    AudioFlushed,
    AudioPacket,
    Connected,
    FmConnectionError,
    SvxReflectorClient,
)
from carendmr.svxreflector.config import (
    FmConfigError,
    FmFunknetzConfig,
    load_fm_config,
)

ROOT = Path(__file__).resolve().parents[1]
KEY = "geheimer-test-key"


# ------------------------------------------------------------- Protokoll

def test_hmac_sha1_matches_reference_vector():
    digest = p.auth_digest("key", b"The quick brown fox jumps over the lazy dog")
    assert digest.hex() == "de7c9b85b8b78aa6bc8a7a36f70a90701c9db4d9"


def test_auth_response_layout_callsign_then_digest():
    challenge = bytes(range(20))
    message = p.encode_auth_response("DK7EE-APP", KEY, challenge)
    assert struct.unpack(">H", message[:2])[0] == p.MSG_AUTH_RESPONSE
    assert message[2:4] == struct.pack(">H", 9) and message[4:13] == b"DK7EE-APP"
    assert message[13:15] == struct.pack(">H", 20)
    assert message[15:] == p.auth_digest(KEY, challenge)
    # Vor der Anmeldung erlaubt der Server höchstens 64 Byte pro Rahmen.
    assert len(p.frame(message)) <= 64


def test_proto_ver_select_tg_monitor_heartbeat():
    assert p.encode_proto_ver() == struct.pack(">HHH", 5, 2, 0)
    assert p.encode_select_tg(20) == struct.pack(">HI", 106, 20)
    assert p.encode_tg_monitor([262, 20, 20]) == struct.pack(">HHII", 107, 2, 20, 262)
    assert p.encode_heartbeat() == struct.pack(">H", 1)


def test_frame_buffer_handles_split_and_joined_frames():
    buffer = p.FrameBuffer()
    data = p.frame(p.encode_heartbeat()) + p.frame(p.encode_select_tg(20))
    assert buffer.feed(data[:3]) == []
    messages = buffer.feed(data[3:])
    assert [p.decode_message(m) for m in messages] == [p.Heartbeat(), p.decode_message(p.encode_select_tg(20))]


def test_frame_buffer_rejects_oversized_frame():
    with pytest.raises(p.ProtocolError):
        p.FrameBuffer().feed(struct.pack(">I", p.MAX_FRAME_SIZE + 1))


def _text(value: str) -> bytes:
    data = value.encode()
    return struct.pack(">H", len(data)) + data


def test_decode_server_messages():
    info = struct.pack(">HHH", 100, 0, 7) + struct.pack(">H", 1) + _text("DB0ABC") + struct.pack(">H", 1) + _text("OPUS")
    assert p.decode_message(info) == p.ServerInfo(7, ("DB0ABC",), ("OPUS",))
    assert p.decode_message(struct.pack(">HHH", 100, 0, 9)) == p.ServerInfo(9)
    assert p.decode_message(struct.pack(">H", 10) + struct.pack(">H", 3) + b"abc") == p.AuthChallenge(b"abc")
    assert p.decode_message(struct.pack(">H", 13) + _text("Access denied")) == p.ServerError("Access denied")
    assert p.decode_message(struct.pack(">HHH", 6, 3, 0)) == p.ProtoVerDowngrade(3, 0)
    assert p.decode_message(struct.pack(">HI", 104, 20) + _text("DL1ABC")) == p.TalkerStart(20, "DL1ABC")
    assert p.decode_message(struct.pack(">H", 105) + _text("DL1ABC")) == p.TalkerStop(0, "DL1ABC")
    assert p.decode_message(struct.pack(">HI", 109, 262)) == p.RequestQsy(262)
    assert isinstance(p.decode_message(struct.pack(">H", 999)), p.UnknownMessage)
    with pytest.raises(p.ProtocolError):
        p.decode_message(struct.pack(">H", 13) + struct.pack(">H", 50) + b"kurz")


def test_udp_roundtrip():
    datagram = p.encode_udp(p.UDP_AUDIO, 7, 65535, b"\x01\x02")
    assert datagram == struct.pack(">HHHH", 101, 7, 65535, 2) + b"\x01\x02"
    assert p.decode_udp(datagram) == p.UdpMessage(101, 7, 65535, b"\x01\x02")
    assert p.encode_udp(p.UDP_HEARTBEAT, 7, 1) == struct.pack(">HHH", 1, 7, 1)


def test_base_callsign():
    assert p.base_callsign("dk7ee-app") == "DK7EE"
    assert p.base_callsign("DB0XYZ") == "DB0XYZ"


# ---------------------------------------------------------- Konfiguration

def _write_config(root: Path, **values) -> None:
    data = {"callsign": "dk7ee-app", "auth_key": KEY}
    data.update(values)
    (root / "config").mkdir(exist_ok=True)
    (root / "config" / "fm_funknetz.local.json").write_text(json.dumps(data), encoding="utf-8")


def test_config_defaults_and_secret_not_in_repr(tmp_path):
    _write_config(tmp_path)
    config = load_fm_config(tmp_path)
    assert config.callsign == "DK7EE-APP"
    assert (config.host, config.port, config.talkgroup) == ("fm-funknetz.de", 5308, 20)
    assert KEY not in repr(config)


def test_config_missing_or_placeholder(tmp_path):
    with pytest.raises(FmConfigError, match="fm_funknetz.local.json fehlt"):
        load_fm_config(tmp_path)
    example = json.loads((ROOT / "config" / "fm_funknetz.example.json").read_text(encoding="utf-8"))
    (tmp_path / "config" / "fm_funknetz.local.json").parent.mkdir(exist_ok=True)
    (tmp_path / "config" / "fm_funknetz.local.json").write_text(json.dumps(example), encoding="utf-8")
    with pytest.raises(FmConfigError, match="Rufzeichen"):
        load_fm_config(tmp_path)
    _write_config(tmp_path, auth_key="KEY_VOM_NETZBETREIBER")
    with pytest.raises(FmConfigError, match="Key"):
        load_fm_config(tmp_path)
    _write_config(tmp_path, port=0)
    with pytest.raises(FmConfigError, match="Port"):
        load_fm_config(tmp_path)


def test_example_config_has_no_real_secret():
    example = json.loads((ROOT / "config" / "fm_funknetz.example.json").read_text(encoding="utf-8"))
    assert example["auth_key"] == "KEY_VOM_NETZBETREIBER"
    assert example["talkgroup"] == 20
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "*.local.json" in gitignore


def test_parser_fm_listen_options():
    args = _build_parser().parse_args(["--fm-listen", "--tg", "9990", "--duration", "60"])
    assert args.fm_listen and args.tg == 9990 and args.duration == 60


def test_fm_modules_are_qt_free():
    for name in ("protocol.py", "client.py", "config.py", "opus.py", "listen.py"):
        text = (ROOT / "carendmr" / "svxreflector" / name).read_text(encoding="utf-8")
        assert "PySide6" not in text


# ------------------------------------------------- lokaler Test-Reflektor

def _opus_available() -> bool:
    try:
        from carendmr.svxreflector.opus import load_libopus

        load_libopus()
        return True
    except Exception:
        return False


class FakeReflector:
    """Minimaler SvxReflector 2.0 auf 127.0.0.1 (TCP und UDP, gleicher Port)."""

    def __init__(self, *, key: str = KEY, audio_packets: list[bytes] | None = None) -> None:
        self.key = key
        self.audio_packets = audio_packets or [b"\xf8\xff\xfe"]
        self.tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for _ in range(20):
            self.tcp.bind(("127.0.0.1", 0))
            self.port = self.tcp.getsockname()[1]
            try:
                self.udp.bind(("127.0.0.1", self.port))
                break
            except OSError:
                self.tcp.close()
                self.tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp.listen(1)
        self.received: list[object] = []
        self.udp_received: list[p.UdpMessage] = []
        self.auth_ok = False
        self.done = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _send(self, conn, message: bytes) -> None:
        conn.sendall(p.frame(message))

    def _read(self, conn, frames: p.FrameBuffer) -> list[bytes]:
        data = conn.recv(4096)
        if not data:
            raise ConnectionError
        return frames.feed(data)

    def _run(self) -> None:
        conn, _ = self.tcp.accept()
        conn.settimeout(5)
        frames = p.FrameBuffer()
        try:
            msgs = self._read(conn, frames)
            assert msgs[0] == p.encode_proto_ver()
            challenge = os.urandom(20)
            self._send(conn, struct.pack(">H", 10) + struct.pack(">H", 20) + challenge)
            msgs = self._read(conn, frames)
            response = msgs[0]
            expected = p.encode_auth_response("DK7EE-APP", self.key, challenge)
            if response != expected:
                self._send(conn, struct.pack(">H", 13) + _text("Access denied"))
                return
            self.auth_ok = True
            self._send(conn, struct.pack(">H", 12))
            self._send(conn, struct.pack(">HHH", 100, 0, 7) + struct.pack(">H", 0) + struct.pack(">H", 1) + _text("OPUS"))
            while len(self.received) < 3:
                for raw in self._read(conn, frames):
                    self.received.append(raw)
            self.udp.settimeout(5)
            data, client_addr = self.udp.recvfrom(2048)
            self.udp_received.append(p.decode_udp(data))
            self._send(conn, struct.pack(">HI", 104, 20) + _text("DB0TST"))
            sequences = [0, 1, 3] + list(range(4, 4 + len(self.audio_packets) - 3))
            for seq, packet in zip(sequences, self.audio_packets):
                self.udp.sendto(p.encode_udp(p.UDP_AUDIO, 7, seq, packet), client_addr)
            self.udp.sendto(p.encode_udp(p.UDP_FLUSH_SAMPLES, 7, 99), client_addr)
            data, _ = self.udp.recvfrom(2048)
            self.udp_received.append(p.decode_udp(data))
            self._send(conn, struct.pack(">HI", 105, 20) + _text("DB0TST"))
            time.sleep(0.3)
        except (OSError, ConnectionError, AssertionError, IndexError):
            pass
        finally:
            self.done.set()
            conn.close()

    def close(self) -> None:
        self.tcp.close()
        self.udp.close()


def _config(port: int, key: str = KEY) -> FmFunknetzConfig:
    return FmFunknetzConfig(
        callsign="DK7EE-APP", auth_key=key, host="127.0.0.1", port=port,
        talkgroup=20, monitor_talkgroups=(9990,), timeout_seconds=5.0,
    )


def _wait_for(events: list, predicate, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if any(predicate(e) for e in list(events)):
            return True
        time.sleep(0.02)
    return False


def test_client_logs_in_selects_tg_and_receives_audio():
    server = FakeReflector(audio_packets=[b"\x01", b"\x02", b"\x03"])
    events: list[object] = []
    client = SvxReflectorClient(_config(server.port), events.append)
    try:
        connected = client.connect()
        assert connected == Connected(7, 20, (), ("OPUS",))
        assert _wait_for(events, lambda e: isinstance(e, p.TalkerStop))
        assert server.done.wait(5)
    finally:
        client.close()
        server.close()
    assert server.auth_ok
    decoded = [p.decode_message(raw) for raw in server.received]
    assert isinstance(decoded[0], p.UnknownMessage) and decoded[0].msg_type == p.MSG_NODE_INFO
    info = json.loads(decoded[0].payload[2:].decode())
    assert info["sw"] == "CarenFM" and info["callsign"] == "DK7EE-APP"
    assert KEY not in decoded[0].payload.decode()
    assert server.received[1] == p.encode_select_tg(20)
    assert server.received[2] == p.encode_tg_monitor([9990])
    assert server.udp_received[0].msg_type == p.UDP_HEARTBEAT and server.udp_received[0].client_id == 7
    assert server.udp_received[1].msg_type == p.UDP_ALL_SAMPLES_FLUSHED
    audio = [e for e in events if isinstance(e, AudioPacket)]
    assert [(a.opus, a.lost_before) for a in audio] == [(b"\x01", 0), (b"\x02", 0), (b"\x03", 1)]
    assert any(isinstance(e, AudioFlushed) for e in events)
    assert p.TalkerStart(20, "DB0TST") in events


def test_wrong_key_is_reported():
    server = FakeReflector(key="anderer-key")
    client = SvxReflectorClient(_config(server.port), lambda e: None)
    try:
        with pytest.raises(FmConnectionError, match="Access denied"):
            client.connect()
    finally:
        client.close()
        server.close()


def test_unreachable_server_is_reported():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    client = SvxReflectorClient(_config(port), lambda e: None)
    with pytest.raises(FmConnectionError, match="nicht erreichbar"):
        client.connect()


@pytest.mark.skipif(not _opus_available(), reason="libopus nicht installiert")
def test_opus_roundtrip_and_concealment():
    from carendmr.svxreflector.opus import OpusDecoder, OpusEncoder

    encoder, decoder = OpusEncoder(16000), OpusDecoder(16000)
    try:
        tone = [int(8000 * math.sin(2 * math.pi * 440 * n / 16000)) for n in range(320)]
        packets = [encoder.encode(tone) for _ in range(10)]
        out = [decoder.decode(packet) for packet in packets]
        assert all(len(frame) == 320 for frame in out)
        assert max(abs(v) for v in out[-1]) > 2000
        assert len(decoder.decode(None)) == 320
    finally:
        encoder.close()
        decoder.close()


@pytest.mark.skipif(not _opus_available(), reason="libopus nicht installiert")
def test_receiver_decodes_audio_and_announces_talker():
    from carendmr.svxreflector.listen import FmReceiver
    from carendmr.svxreflector.opus import OpusDecoder, OpusEncoder

    encoder = OpusEncoder(16000)
    tone = [int(8000 * math.sin(2 * math.pi * 440 * n / 16000)) for n in range(320)]
    packets = [encoder.encode(tone) for _ in range(6)]
    encoder.close()
    server = FakeReflector(audio_packets=packets)

    class FakeOutput:
        def __init__(self):
            self.samples: list[int] = []
            self.started = self.closed = False

        def start(self):
            self.started = True

        def write(self, samples):
            self.samples.extend(samples)

        def close(self):
            self.closed = True

    output = FakeOutput()
    said: list[str] = []
    receiver = FmReceiver(_config(server.port), decoder=OpusDecoder(16000), output=output, say=said.append)
    try:
        receiver.start()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not any("fertig" in s for s in said):
            receiver.process(0.1)
    finally:
        receiver.close()
        server.close()
    assert output.started and output.closed
    assert any("DB0TST spricht (Talkgroup 20)" in s for s in said)
    assert any("DB0TST fertig" in s for s in said)
    assert receiver.stats.audio_packets == 6
    assert receiver.stats.concealed_frames == 1
    assert len(output.samples) == 7 * 320
