"""Audio-Backend-Schnittstelle und sounddevice-Implementierung."""

from __future__ import annotations

from typing import Any, Callable, Protocol, Sequence

from .devices import AudioDevice


class AudioBackend(Protocol):
    """Abstraktion, damit die Logik ohne Audiohardware testbar bleibt."""

    def query_devices(self) -> list[AudioDevice]:
        """Liefert alle verfügbaren Geräte."""

    def record_input(
        self,
        *,
        input_index: int,
        duration_seconds: float,
        sample_rate: int,
        channels: int,
        level_callback: Callable[[float], None] | None = None,
    ) -> Any:
        """Nimmt PCM lokal auf und liefert die Samples."""

    def play_samples(
        self,
        samples: Any,
        *,
        output_index: int,
        sample_rate: int,
    ) -> None:
        """Spielt zuvor aufgenommene PCM-Samples lokal ab."""

    def record_and_play(
        self,
        *,
        input_index: int,
        output_index: int,
        duration_seconds: float,
        sample_rate: int,
        channels: int,
    ) -> None:
        """Nimmt lokal auf und spielt die Aufnahme anschließend ab."""


class SoundDeviceBackend:
    """PortAudio-Zugriff über die Bibliothek sounddevice."""

    def __init__(self) -> None:
        self._sd: Any | None = None

    def _module(self) -> Any:
        if self._sd is not None:
            return self._sd
        try:
            import sounddevice as sd
        except ImportError as exc:
            raise RuntimeError(
                "Die Audio-Bibliothek sounddevice ist nicht installiert. "
                "Bitte führen Sie 'python -m pip install -r requirements.txt' aus."
            ) from exc
        self._sd = sd
        return sd

    def query_devices(self) -> list[AudioDevice]:
        sd = self._module()
        raw_devices: Sequence[Any] = sd.query_devices()
        raw_hostapis: Sequence[Any] = sd.query_hostapis()

        default_input, default_output = self._normalize_defaults(
            getattr(sd.default, "device", (-1, -1))
        )

        devices: list[AudioDevice] = []
        for index, raw in enumerate(raw_devices):
            host_index = int(raw["hostapi"])
            host_api = str(raw_hostapis[host_index]["name"])
            devices.append(
                AudioDevice(
                    index=index,
                    name=str(raw["name"]),
                    host_api=host_api,
                    max_input_channels=int(raw["max_input_channels"]),
                    max_output_channels=int(raw["max_output_channels"]),
                    default_sample_rate=float(raw["default_samplerate"]),
                    is_default_input=index == default_input,
                    is_default_output=index == default_output,
                )
            )
        return devices

    @staticmethod
    def _normalize_defaults(value: Any) -> tuple[int, int]:
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            return int(value[0]), int(value[1])
        return -1, -1

    def record_input(
        self,
        *,
        input_index: int,
        duration_seconds: float,
        sample_rate: int,
        channels: int,
        level_callback: Callable[[float], None] | None = None,
    ) -> Any:
        if duration_seconds <= 0:
            raise ValueError("Die Aufnahmedauer muss größer als null sein.")
        sd = self._module()
        import numpy as np

        target_frames = int(round(duration_seconds * sample_rate))
        blocks: list[Any] = []
        captured = 0

        def callback(indata: Any, frames: int, _time: Any, status: Any) -> None:
            nonlocal captured
            del status
            remaining = target_frames - captured
            if remaining <= 0:
                raise sd.CallbackStop
            block = indata[:remaining].copy()
            blocks.append(block)
            captured += int(block.shape[0])
            if level_callback is not None and block.size:
                rms = float(np.sqrt(np.mean(np.square(block, dtype=np.float64))))
                level_callback(min(100.0, rms * 200.0))
            if captured >= target_frames:
                raise sd.CallbackStop

        with sd.InputStream(
            samplerate=sample_rate,
            channels=channels,
            dtype="float32",
            device=input_index,
            callback=callback,
        ):
            while captured < target_frames:
                sd.sleep(20)
        if not blocks:
            return np.empty((0, channels), dtype="float32")
        return np.concatenate(blocks, axis=0)[:target_frames]

    def play_samples(
        self,
        samples: Any,
        *,
        output_index: int,
        sample_rate: int,
    ) -> None:
        sd = self._module()
        sd.play(samples, samplerate=sample_rate, device=output_index)
        sd.wait()

    def record_and_play(
        self,
        *,
        input_index: int,
        output_index: int,
        duration_seconds: float,
        sample_rate: int,
        channels: int,
    ) -> None:
        if duration_seconds <= 0:
            raise ValueError("Die Aufnahmedauer muss größer als null sein.")
        sd = self._module()
        frames = int(duration_seconds * sample_rate)
        recording = sd.rec(
            frames,
            samplerate=sample_rate,
            channels=channels,
            dtype="float32",
            device=input_index,
        )
        sd.wait()
        sd.play(
            recording,
            samplerate=sample_rate,
            device=output_index,
        )
        sd.wait()
