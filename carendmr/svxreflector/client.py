"""Verbindung zu einem SvxReflector (FM-Funknetz), Protokoll 2.0.

0.2.1.95: nur Anmelden und Empfangen – dieser Client sendet keine Sprache.
"""
from __future__ import annotations

import socket
import threading
import time
from dataclasses import dataclass
from typing import Callable

from carendmr.version import __version__

from . import protocol as p
from .config import FmFunknetzConfig


class FmConnectionError(RuntimeError):
    """Verbindung oder Anmeldung beim Reflektor fehlgeschlagen."""


@dataclass(frozen=True)
class Connected:
    client_id: int
    talkgroup: int
    nodes: tuple[str, ...]
    codecs: tuple[str, ...]


@dataclass(frozen=True)
class AudioPacket:
    sequence: int
    opus: bytes
    lost_before: int = 0  # fehlende Pakete direkt davor (für Verschleierung)


@dataclass(frozen=True)
class AudioFlushed:
    pass


@dataclass(frozen=True)
class Disconnected:
    reason: str


EventCallback = Callable[[object], None]


def node_info(callsign: str) -> dict:
    return {
        "sw": "CarenDMR",
        "swVer": __version__,
        "callsign": callsign,
        "Website": "https://dk7ee.de/carendmr.html",
    }


class SvxReflectorClient:
    """Meldet sich an, wählt eine Talkgroup und liefert Ereignisse.

    Ereignisse (über ``on_event``, aus Hintergrund-Threads): ``Connected``,
    ``protocol.TalkerStart``/``TalkerStop``, ``protocol.NodeJoined``/``NodeLeft``,
    ``protocol.RequestQsy``, ``AudioPacket``, ``AudioFlushed``, ``Disconnected``.
    """

    def __init__(
        self,
        config: FmFunknetzConfig,
        on_event: EventCallback,
        *,
        tcp_heartbeat_seconds: float = p.TCP_HEARTBEAT_INTERVAL_SECONDS,
        tcp_timeout_seconds: float = p.TCP_HEARTBEAT_TIMEOUT_SECONDS,
        udp_heartbeat_seconds: float = p.UDP_HEARTBEAT_INTERVAL_SECONDS,
    ) -> None:
        config.validate()
        self.config = config
        self._on_event = on_event
        self._tcp_heartbeat = tcp_heartbeat_seconds
        self._tcp_timeout = tcp_timeout_seconds
        self._udp_heartbeat = udp_heartbeat_seconds
        self._tcp: socket.socket | None = None
        self._udp: socket.socket | None = None
        self._send_lock = threading.Lock()
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []
        self._frames = p.FrameBuffer()
        self._client_id = 0
        self._udp_sequence = 0
        self._last_rx_sequence: int | None = None
        self._last_tcp_rx = 0.0
        self.talkgroup = config.talkgroup
        self.connected = False

    # -------------------------------------------------------------- Aufbau
    def connect(self) -> Connected:
        """Baut TCP auf, meldet sich an und startet Empfang und Heartbeats."""
        cfg = self.config
        try:
            tcp = socket.create_connection((cfg.host, cfg.port), timeout=cfg.timeout_seconds)
        except OSError as error:
            raise FmConnectionError(
                f"Server {cfg.host}:{cfg.port} nicht erreichbar: {error}"
            ) from error
        self._tcp = tcp
        try:
            tcp.settimeout(cfg.timeout_seconds)
            self._send(p.encode_proto_ver())
            info = self._handshake()
            peer = tcp.getpeername()
            udp = socket.socket(socket.AF_INET6 if ":" in peer[0] else socket.AF_INET, socket.SOCK_DGRAM)
            udp.connect((peer[0], cfg.port))
            udp.settimeout(0.5)
            self._udp = udp
            self._client_id = info.client_id
            self._send(p.encode_node_info(node_info(cfg.callsign)))
            self._send(p.encode_select_tg(self.talkgroup))
            self._send(p.encode_tg_monitor(cfg.monitor_talkgroups))
            self._send_udp_heartbeat()
        except Exception:
            self.close()
            raise
        tcp.settimeout(0.5)
        self.connected = True
        self._last_tcp_rx = time.monotonic()
        for target, name in (
            (self._tcp_loop, "fm-tcp"),
            (self._udp_loop, "fm-udp"),
            (self._heartbeat_loop, "fm-heartbeat"),
        ):
            thread = threading.Thread(target=target, name=name, daemon=True)
            thread.start()
            self._threads.append(thread)
        event = Connected(info.client_id, self.talkgroup, info.nodes, info.codecs)
        self._on_event(event)
        return event

    def _handshake(self) -> p.ServerInfo:
        deadline = time.monotonic() + self.config.timeout_seconds
        while time.monotonic() < deadline:
            for message in self._read_messages():
                if isinstance(message, p.AuthChallenge):
                    self._send(p.encode_auth_response(
                        self.config.callsign, self.config.auth_key, message.challenge
                    ))
                elif isinstance(message, p.ServerInfo):
                    return message
                elif isinstance(message, p.ServerError):
                    raise FmConnectionError(f"Server meldet: {message.message}")
                elif isinstance(message, p.ProtoVerDowngrade):
                    raise FmConnectionError(
                        "Der Server verlangt Protokoll "
                        f"{message.major}.{message.minor}; CarenDMR spricht 2.0."
                    )
        raise FmConnectionError(
            "Keine Anmeldebestätigung vom Server (Zeitüberschreitung). "
            "Rufzeichen und Key prüfen; die Freischaltung kann bis zu 60 Minuten dauern."
        )

    def _read_messages(self) -> list:
        tcp = self._tcp
        if tcp is None:
            raise FmConnectionError("Keine Verbindung zum Server.")
        try:
            data = tcp.recv(4096)
        except socket.timeout:
            return []
        if not data:
            raise FmConnectionError("Der Server hat die Verbindung getrennt.")
        return [p.decode_message(message) for message in self._frames.feed(data)]

    # ------------------------------------------------------------- Betrieb
    def select_talkgroup(self, talkgroup: int) -> None:
        self._send(p.encode_select_tg(talkgroup))
        self.talkgroup = talkgroup

    def _send(self, message: bytes) -> None:
        tcp = self._tcp
        if tcp is None:
            raise FmConnectionError("Keine Verbindung zum Server.")
        with self._send_lock:
            tcp.sendall(p.frame(message))

    def _send_udp(self, msg_type: int, audio: bytes | None = None) -> None:
        udp = self._udp
        if udp is None:
            return
        datagram = p.encode_udp(msg_type, self._client_id, self._udp_sequence, audio)
        self._udp_sequence = (self._udp_sequence + 1) & 0xFFFF
        udp.send(datagram)

    def _send_udp_heartbeat(self) -> None:
        self._send_udp(p.UDP_HEARTBEAT)

    def _tcp_loop(self) -> None:
        try:
            while not self._stop.is_set():
                messages = self._read_messages()
                if messages:
                    self._last_tcp_rx = time.monotonic()
                for message in messages:
                    if isinstance(message, (p.Heartbeat, p.UnknownMessage, p.ProtoVer, p.AuthOk)):
                        continue
                    if isinstance(message, p.ServerError):
                        self._finish(f"Server meldet: {message.message}")
                        return
                    if isinstance(message, p.RequestQsy):
                        self.select_talkgroup(message.talkgroup)
                    self._on_event(message)
                if time.monotonic() - self._last_tcp_rx > self._tcp_timeout:
                    self._finish("Keine Lebenszeichen vom Server (Zeitüberschreitung).")
                    return
        except (OSError, FmConnectionError, p.ProtocolError) as error:
            if not self._stop.is_set():
                self._finish(str(error))

    def _udp_loop(self) -> None:
        udp = self._udp
        if udp is None:
            return
        while not self._stop.is_set():
            try:
                datagram = udp.recv(2048)
            except socket.timeout:
                continue
            except OSError as error:
                if not self._stop.is_set():
                    self._finish(f"UDP-Fehler: {error}")
                return
            try:
                message = p.decode_udp(datagram)
            except p.ProtocolError:
                continue
            if message.msg_type == p.UDP_AUDIO and message.audio:
                lost = 0
                if self._last_rx_sequence is not None:
                    gap = (message.sequence - self._last_rx_sequence - 1) & 0xFFFF
                    if gap > 0x8000:
                        continue  # verspätetes, älteres Paket verwerfen
                    lost = min(gap, 5)
                self._last_rx_sequence = message.sequence
                self._on_event(AudioPacket(message.sequence, message.audio, lost))
            elif message.msg_type == p.UDP_FLUSH_SAMPLES:
                self._last_rx_sequence = None
                self._send_udp(p.UDP_ALL_SAMPLES_FLUSHED)
                self._on_event(AudioFlushed())

    def _heartbeat_loop(self) -> None:
        next_tcp = time.monotonic() + self._tcp_heartbeat
        next_udp = time.monotonic() + self._udp_heartbeat
        while not self._stop.wait(0.25):
            now = time.monotonic()
            try:
                if now >= next_tcp:
                    self._send(p.encode_heartbeat())
                    next_tcp = now + self._tcp_heartbeat
                if now >= next_udp:
                    self._send_udp_heartbeat()
                    next_udp = now + self._udp_heartbeat
            except (OSError, FmConnectionError) as error:
                if not self._stop.is_set():
                    self._finish(f"Senden fehlgeschlagen: {error}")
                return

    # --------------------------------------------------------------- Ende
    def _finish(self, reason: str) -> None:
        if self._stop.is_set():
            return
        self.close()
        self._on_event(Disconnected(reason))

    def close(self) -> None:
        self._stop.set()
        self.connected = False
        for sock in (self._tcp, self._udp):
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass
        self._tcp = None
        self._udp = None
        current = threading.current_thread()
        for thread in self._threads:
            if thread is not current:
                thread.join(timeout=2.0)
        self._threads = []
