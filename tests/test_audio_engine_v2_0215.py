from __future__ import annotations

import numpy as np

from carendmr.audio.backend import SoundDeviceBackend
from carendmr.version import __version__


class _FakeSoundDevice:
    def __init__(self) -> None:
        self.checked: list[int] = []

    def query_devices(self, index: int):
        assert index == 7
        return {"default_samplerate": 48000.0}

    def check_input_settings(self, *, device, channels, dtype, samplerate):
        assert device == 7
        assert channels == 1
        assert dtype == "float32"
        self.checked.append(int(samplerate))
        if int(samplerate) != 48000:
            raise RuntimeError("unsupported")


def test_release_version_0215() -> None:
    assert __version__ == "0.2.1.9"


def test_audio_engine_uses_native_rate_when_target_is_rejected() -> None:
    backend = SoundDeviceBackend()
    fake = _FakeSoundDevice()
    backend._sd = fake
    assert backend.resolve_input_sample_rate(7, 16000, 1) == 48000
    assert fake.checked[:2] == [16000, 48000]


def test_audio_engine_resamples_native_input_to_common_rate() -> None:
    source = np.sin(2 * np.pi * 1000 * np.arange(4800) / 48000).astype(np.float32)
    converted = SoundDeviceBackend._resample(source, 48000, 16000)
    assert converted.dtype == np.float32
    assert abs(len(converted) - 1600) <= 1
    assert float(np.max(np.abs(converted))) > 0.9
