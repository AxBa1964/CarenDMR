"""Audio-Grundlage von CarenDMR."""

from .backend import AudioBackend, SoundDeviceBackend
from .devices import AudioDevice, AudioDirection, AudioSelection
from .manager import (
    AudioConfigurationError,
    AudioManager,
    AudioUnavailableError,
)
from .pcm_output import BufferedPcmOutput, PcmOutputError

__all__ = [
    "AudioBackend",
    "AudioConfigurationError",
    "AudioDevice",
    "AudioDirection",
    "AudioManager",
    "AudioSelection",
    "AudioUnavailableError",
    "BufferedPcmOutput",
    "PcmOutputError",
    "SoundDeviceBackend",
]
