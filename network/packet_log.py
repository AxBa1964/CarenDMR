"""Protokollunabhängige, lesbare Paketdiagnose für Netzwerkdaten."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TextIO
import sys


@dataclass(slots=True)
class PacketLogger:
    """Schreibt Netzwerkpakete mit Richtung, Hexwerten und ASCII-Darstellung."""

    enabled: bool = False
    stream: TextIO = sys.stdout
    bytes_per_line: int = 16
    include_timestamp: bool = True

    def log(
        self,
        direction: str,
        protocol: str,
        packet_name: str,
        packet: bytes,
    ) -> None:
        if not self.enabled:
            return
        if direction not in {"TX", "RX"}:
            raise ValueError("Die Paketrichtung muss TX oder RX sein.")
        if self.bytes_per_line <= 0:
            raise ValueError("bytes_per_line muss größer als null sein.")

        timestamp = (
            datetime.now().astimezone().isoformat(timespec="milliseconds") + " "
            if self.include_timestamp
            else ""
        )
        title = (
            f"{timestamp}[{direction}] {protocol} {packet_name} "
            f"({len(packet)} Bytes)"
        )
        separator = "=" * 86

        print(file=self.stream)
        print(separator, file=self.stream)
        print(title, file=self.stream)
        print(separator, file=self.stream)

        for offset in range(0, len(packet), self.bytes_per_line):
            chunk = packet[offset : offset + self.bytes_per_line]
            hex_part = " ".join(f"{value:02X}" for value in chunk)
            ascii_part = "".join(
                chr(value) if 32 <= value < 127 else "." for value in chunk
            )
            width = self.bytes_per_line * 3 - 1
            print(
                f"{offset:04X}  {hex_part:<{width}}  {ascii_part}",
                file=self.stream,
            )

        print(separator, file=self.stream)
        self.stream.flush()


def identify_ascii_packet(packet: bytes) -> str:
    """Ermittelt für Diagnosezwecke den bekannten ASCII-Paketnamen."""

    known_prefixes = (
        b"MSTPONG",
        b"RPTPING",
        b"RPTACK",
        b"MSTNAK",
        b"RPTCL",
        b"RPTL",
        b"RPTK",
        b"RPTC",
        b"DMRD",
    )
    for prefix in known_prefixes:
        if packet.startswith(prefix):
            return prefix.decode("ascii")
    return "UNKNOWN"
