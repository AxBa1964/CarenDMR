"""Vorbereitete Schnittstelle für spätere USB-AMBE-Hardware."""

from __future__ import annotations

from .base import AmbeEncoder, EncoderUnavailableError


class UsbAmbeEncoder(AmbeEncoder):
    """Platzhalter-Backend; enthält in 0.0.19.4 noch keine Geräteansteuerung."""

    def __init__(self, *_: object, **__: object) -> None:
        raise EncoderUnavailableError(
            "USB-AMBE-Hardware ist als Backend vorgesehen, aber in 0.0.19.4 noch nicht implementiert."
        )

    def encode_2450x1150(self, pcm_samples: tuple[int, ...]) -> bytes:
        raise EncoderUnavailableError("USB-AMBE-Hardware ist noch nicht implementiert.")

    def close(self) -> None:
        return None
