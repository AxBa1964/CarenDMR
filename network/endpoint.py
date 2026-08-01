"""DNS-Auflösung für UDP-Endpunkte."""

from __future__ import annotations

import socket
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResolvedEndpoint:
    host: str
    port: int
    family: int
    sockaddr: tuple

    @property
    def address_text(self) -> str:
        return str(self.sockaddr[0])

    @property
    def family_name(self) -> str:
        if self.family == socket.AF_INET6:
            return "IPv6"
        if self.family == socket.AF_INET:
            return "IPv4"
        return f"Adressfamilie {self.family}"


def resolve_udp_endpoint(host: str, port: int) -> ResolvedEndpoint:
    """Löst einen Hostnamen in einen nutzbaren UDP-Endpunkt auf."""
    try:
        results = socket.getaddrinfo(
            host,
            port,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_DGRAM,
            proto=socket.IPPROTO_UDP,
        )
    except socket.gaierror as exc:
        raise OSError(
            f"Der Servername '{host}' konnte nicht aufgelöst werden."
        ) from exc

    if not results:
        raise OSError(
            f"Für den Server '{host}' wurde keine UDP-Adresse gefunden."
        )

    # IPv4 zuerst, weil die meisten heutigen DMR-Master darüber erreichbar sind.
    results = sorted(
        results,
        key=lambda item: 0 if item[0] == socket.AF_INET else 1,
    )
    family, _, _, _, sockaddr = results[0]
    return ResolvedEndpoint(
        host=host,
        port=port,
        family=family,
        sockaddr=sockaddr,
    )
