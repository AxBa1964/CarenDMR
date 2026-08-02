"""Abstrakte AMBE-Encoder-Grenze für optionale externe Vocoder."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

PCM_SAMPLES_PER_FRAME = 160
AMBE_BYTES_PER_FRAME = 9


class EncoderError(RuntimeError):
    """Basisklasse für kontrollierte Encoderfehler."""


class EncoderUnavailableError(EncoderError):
    """Der konfigurierte Encoder ist nicht verfügbar."""


class EncoderValidationError(EncoderError):
    """Ein Encoder oder seine Ausgabe ist ungültig."""


@dataclass(frozen=True, slots=True)
class EncoderDiagnostics:
    backend: str
    plugin_path: str
    ready: bool
    encoded_bytes: int
    message: str


class AmbeEncoder(ABC):
    """Neutrale Schnittstelle für AMBE+2 2450/1150-Encoding."""

    @abstractmethod
    def encode_2450x1150(self, pcm_samples: tuple[int, ...]) -> bytes:
        """Kodiert exakt 160 PCM-Samples in einen 72-Bit-AMBE-Rahmen."""

    @abstractmethod
    def close(self) -> None:
        """Gibt native Ressourcen frei."""
