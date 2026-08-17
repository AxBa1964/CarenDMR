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
    "OptimizerDiagnostics", "optimize_transmit_pcm", "StreamingTxSpeechProcessor",
    "TxAudioTunerSettings", "StreamingTxAudioTuner", "TUNER_PRESETS", "tuner_preset",
]

from .optimizer import OptimizerDiagnostics, StreamingTxSpeechProcessor, optimize_transmit_pcm

from .tuner import TxAudioTunerSettings, StreamingTxAudioTuner, PRESETS as TUNER_PRESETS, preset as tuner_preset
