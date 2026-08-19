"""Receive-only vocoder interfaces."""

from .base import (
    AMBE_CODEWORD_SIZE,
    PCM_SAMPLES_PER_CODEWORD,
    PcmFrame,
    ReceiveVocoder,
    VocoderDecodeError,
    VocoderUnavailableError,
)
from .native import NativeMbeReceiveVocoder
from .md380_dynarmic import Md380DynarmicReceiveVocoder


def extract_ambe_codewords(*args, **kwargs):
    """Lazy import avoids brandmeister <-> vocoder package initialization cycle."""
    from .dmr import extract_ambe_codewords as _extract_ambe_codewords
    return _extract_ambe_codewords(*args, **kwargs)


__all__ = [
    "AMBE_CODEWORD_SIZE",
    "PCM_SAMPLES_PER_CODEWORD",
    "NativeMbeReceiveVocoder",
    "Md380DynarmicReceiveVocoder",
    "PcmFrame",
    "ReceiveVocoder",
    "VocoderDecodeError",
    "VocoderUnavailableError",
    "extract_ambe_codewords",
]
