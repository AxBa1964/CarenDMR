"""Kleine, testbare UDP-Transportschicht."""

from __future__ import annotations

import socket
from typing import Callable

from .endpoint import ResolvedEndpoint


class NetworkTransportError(RuntimeError):
    """Ein UDP-Transportvorgang ist fehlgeschlagen."""


class NetworkReceiveTimeout(NetworkTransportError):
    """Innerhalb des Zeitlimits wurde kein UDP-Paket empfangen."""


SocketFactory = Callable[[int, int, int], socket.socket]


class UdpTransport:
    def __init__(
        self,
        endpoint: ResolvedEndpoint,
        *,
        timeout_seconds: float = 3.0,
        socket_factory: SocketFactory = socket.socket,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("Das Zeitlimit muss größer als null sein.")
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds
        self.socket_factory = socket_factory
        self._socket: socket.socket | None = None

    @property
    def is_open(self) -> bool:
        return self._socket is not None

    def open(self) -> None:
        if self.is_open:
            return
        try:
            sock = self.socket_factory(
                self.endpoint.family,
                socket.SOCK_DGRAM,
                socket.IPPROTO_UDP,
            )
            sock.settimeout(self.timeout_seconds)
            sock.connect(self.endpoint.sockaddr)
        except OSError as exc:
            raise NetworkTransportError(
                "Der UDP-Netzwerkkanal konnte nicht geöffnet werden."
            ) from exc
        self._socket = sock

    def send(self, payload: bytes) -> int:
        if not payload:
            raise ValueError("Ein leeres UDP-Paket wird nicht gesendet.")
        sock = self._require_socket()
        try:
            return int(sock.send(payload))
        except OSError as exc:
            raise NetworkTransportError(
                "Das UDP-Paket konnte nicht gesendet werden."
            ) from exc

    def receive(self, max_bytes: int = 2048) -> bytes:
        if max_bytes <= 0:
            raise ValueError("Die maximale Paketgröße muss größer als null sein.")
        sock = self._require_socket()
        try:
            return bytes(sock.recv(max_bytes))
        except socket.timeout as exc:
            raise NetworkReceiveTimeout(
                "Der Server hat innerhalb des Zeitlimits nicht geantwortet."
            ) from exc
        except OSError as exc:
            raise NetworkTransportError(
                "Beim Empfang eines UDP-Pakets ist ein Fehler aufgetreten."
            ) from exc

    def close(self) -> None:
        sock, self._socket = self._socket, None
        if sock is not None:
            sock.close()

    def _require_socket(self) -> socket.socket:
        if self._socket is None:
            raise NetworkTransportError(
                "Der UDP-Netzwerkkanal ist nicht geöffnet."
            )
        return self._socket

    def __enter__(self) -> "UdpTransport":
        self.open()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()
