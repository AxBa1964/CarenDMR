"""Optionale, vom CarenDMR-Kern entkoppelte AMBE-Encoder."""

from .base import (
    AMBE_BYTES_PER_FRAME,
    PCM_SAMPLES_PER_FRAME,
    AmbeEncoder,
    EncoderDiagnostics,
    EncoderError,
    EncoderUnavailableError,
    EncoderValidationError,
)
from .plugin import DroidStarPluginEncoder, EncoderSettingsStore, default_bridge_path, verify_plugin
from .usb import UsbAmbeEncoder

__all__ = [
    "AMBE_BYTES_PER_FRAME",
    "PCM_SAMPLES_PER_FRAME",
    "AmbeEncoder",
    "DroidStarPluginEncoder",
    "EncoderDiagnostics",
    "EncoderError",
    "EncoderSettingsStore",
    "EncoderUnavailableError",
    "EncoderValidationError",
    "UsbAmbeEncoder",
    "default_bridge_path",
    "verify_plugin",
]
