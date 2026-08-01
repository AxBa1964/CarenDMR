from __future__ import annotations


def dump_packet(name: str, packet: bytes) -> None:
    """Gibt ein UDP-Paket als Hexdump mit ASCII-Darstellung aus."""

    print()
    print("=" * 78)
    print(f"{name} ({len(packet)} Bytes)")
    print("=" * 78)

    for offset in range(0, len(packet), 16):
        chunk = packet[offset:offset + 16]

        hex_part = " ".join(f"{b:02X}" for b in chunk)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)

        print(f"{offset:04X}  {hex_part:<47} {ascii_part}")

    print("=" * 78)
    print()