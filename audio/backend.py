"""Audio-Backend-Schnittstelle und sounddevice-Implementierung."""

from __future__ import annotations

from typing import Any, Protocol, Sequence

from .devices import AudioDevice


class AudioBackend(Protocol):
    """Abstraktion, damit die Logik ohne Audiohardware testbar bleibt."""

    def query_devices(self) -> list[AudioDevice]:
        """Liefert alle verfügbaren Geräte."""

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
