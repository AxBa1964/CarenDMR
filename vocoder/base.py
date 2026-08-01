"""Stable receive-vocoder boundary, independent of native implementations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


AMBE_CODEWORD_SIZE = 9
PCM_SAMPLES_PER_CODEWORD = 160


class VocoderUnavailableError(RuntimeError):
    """Raised when the selected receive decoder cannot be loaded."""


class VocoderDecodeError(RuntimeError):
    """Raised when a validated codeword cannot be decoded."""


@dataclass(frozen=True, slots=True)
class PcmFrame:
    """One 20 ms, 8 kHz, signed 16-bit mono PCM frame."""

    samples: tuple[int, ...]
    corrected_errors: int

    def __post_init__(self) -> None:
        if len(self.samples) != PCM_SAMPLES_PER_CODEWORD:
            raise ValueError(
                f"PCM benötigt genau {PCM_SAMPLES_PER_CODEWORD} Samples."
            )
        if any(not -32768 <= sample <= 32767 for sample in self.samples):
            raise ValueError("PCM-Samples müssen vorzeichenbehaftete 16-Bit-Werte sein.")
        if self.corrected_errors < 0:
            raise ValueError("Die Fehleranzahl darf nicht negativ sein.")


class ReceiveVocoder(Protocol):
    """Stateful receive-only AMBE codeword decoder."""

    def decode(self, codeword: bytes) -> PcmFrame:
        """Decode one codeword in stream order."""

    def close(self) -> None:
        """Release implementation resources; safe to call repeatedly."""
