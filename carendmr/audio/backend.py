"""Audio-Backend-Schnittstelle und sounddevice-Implementierung."""

from __future__ import annotations

from threading import Event
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

    def record_input_until(
        self,
        *,
        input_index: int,
        stop_event: Event,
        max_duration_seconds: float,
        sample_rate: int,
        channels: int,
        level_callback: Callable[[float], None] | None = None,
    ) -> Any:
        """Nimmt bis zum Loslassen oder bis zum Sicherheitslimit auf."""


    def stream_input_blocks_until(
        self, *, input_index: int, stop_event: Event, max_duration_seconds: float,
        sample_rate: int, channels: int,
        block_callback: Callable[[Any], None],
        level_callback: Callable[[float], None] | None = None,
    ) -> None:
        """Liefert Mikrofonblöcke fortlaufend bis PTT losgelassen wird."""
        sd = self._module()
        import numpy as np
        started = __import__('time').monotonic()

        def callback(indata: Any, _frames: int, _time: Any, status: Any) -> None:
            del status
            if stop_event.is_set() or __import__('time').monotonic() - started >= max_duration_seconds:
                raise sd.CallbackStop
            block = indata.copy()
            if block.size:
                block_callback(block)
                if level_callback is not None:
                    rms = float(np.sqrt(np.mean(np.square(block, dtype=np.float64))))
                    level_callback(min(100.0, rms * 200.0))

        with sd.InputStream(samplerate=sample_rate, channels=channels, dtype="float32",
                            device=input_index, callback=callback, blocksize=320):
            while not stop_event.is_set() and __import__('time').monotonic() - started < max_duration_seconds:
                sd.sleep(10)

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
        self.last_input_stream_info: dict[str, Any] = {}

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

    def resolve_input_sample_rate(self, input_index: int, requested_rate: int, channels: int) -> int:
        """Ermittelt eine vom konkreten Gerät akzeptierte Eingaberate."""
        sd = self._module()
        device = sd.query_devices(input_index)
        candidates = [int(requested_rate), int(round(float(device["default_samplerate"])))]
        candidates.extend((48000, 44100, 32000, 16000, 8000))
        seen: set[int] = set()
        for rate in candidates:
            if rate <= 0 or rate in seen:
                continue
            seen.add(rate)
            try:
                sd.check_input_settings(
                    device=input_index, channels=channels, dtype="float32", samplerate=rate
                )
            except Exception:
                continue
            return rate
        raise RuntimeError(
            f"Das Mikrofon unterstützt keine geeignete Abtastrate (Ziel {requested_rate} Hz)."
        )


    def resolve_output_sample_rate(self, output_index: int, requested_rate: int, channels: int = 1) -> int:
        """Ermittelt eine vom konkreten Ausgabegerät akzeptierte Rate."""
        sd = self._module()
        device = sd.query_devices(output_index)
        candidates = [int(requested_rate), int(round(float(device["default_samplerate"])))]
        candidates.extend((48000, 44100, 32000, 16000, 8000))
        seen: set[int] = set()
        for rate in candidates:
            if rate <= 0 or rate in seen:
                continue
            seen.add(rate)
            try:
                sd.check_output_settings(
                    device=output_index, channels=channels, dtype="float32", samplerate=rate
                )
            except Exception:
                continue
            return rate
        raise RuntimeError(
            f"Das Wiedergabegerät unterstützt keine geeignete Abtastrate (Ziel {requested_rate} Hz)."
        )

    @staticmethod
    def _resample(samples: Any, source_rate: int, target_rate: int) -> Any:
        import numpy as np
        data = np.asarray(samples, dtype=np.float32)
        if source_rate == target_rate or data.size == 0:
            return data
        from math import gcd
        from scipy.signal import resample_poly
        divisor = gcd(int(source_rate), int(target_rate))
        result = resample_poly(
            data, int(target_rate) // divisor, int(source_rate) // divisor, axis=0
        )
        return np.asarray(result, dtype=np.float32)


    def _resolve_capture_channels(self, input_index: int, requested_channels: int) -> int:
        """Uses up to two physical channels for WASAPI and mixes to the requested mono signal.

        Some USB webcam endpoints accept a mono WASAPI stream but place the useful
        signal only on one channel of their native stereo endpoint. Opening both
        channels avoids a successfully opened but silent stream.
        """
        sd = self._module()
        device = sd.query_devices(input_index)
        max_channels = max(1, int(device.get("max_input_channels", requested_channels)))
        try:
            host = sd.query_hostapis(int(device["hostapi"]))
            host_name = str(host.get("name", ""))
        except Exception:
            host_name = ""
        if "WASAPI" in host_name.upper() and max_channels > requested_channels:
            return min(2, max_channels)
        return min(max(1, int(requested_channels)), max_channels)

    @staticmethod
    def _to_requested_channels(samples: Any, requested_channels: int) -> Any:
        """Selects the strongest captured channel and returns a stable mono stream."""
        import numpy as np
        data = np.asarray(samples, dtype=np.float32)
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        if requested_channels == 1 and data.shape[1] > 1:
            energies = np.sqrt(np.mean(np.square(data, dtype=np.float64), axis=0))
            channel = int(np.argmax(energies))
            return data[:, channel:channel + 1]
        return data[:, :requested_channels]

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

        capture_channels = self._resolve_capture_channels(input_index, channels)
        native_rate = self.resolve_input_sample_rate(input_index, sample_rate, capture_channels)
        self.last_input_stream_info = {"device_index": input_index, "requested_rate": int(sample_rate), "native_rate": int(native_rate), "channels": int(channels), "capture_channels": int(capture_channels)}
        target_frames = int(round(duration_seconds * native_rate))
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
            samplerate=native_rate,
            channels=capture_channels,
            dtype="float32",
            device=input_index,
            callback=callback,
        ):
            while captured < target_frames:
                sd.sleep(20)
        if not blocks:
            return np.empty((0, channels), dtype="float32")
        native = self._to_requested_channels(np.concatenate(blocks, axis=0)[:target_frames], channels)
        target_count = int(round(duration_seconds * sample_rate))
        return self._resample(native, native_rate, sample_rate)[:target_count]

    def record_input_until(
        self,
        *,
        input_index: int,
        stop_event: Event,
        max_duration_seconds: float,
        sample_rate: int,
        channels: int,
        level_callback: Callable[[float], None] | None = None,
    ) -> Any:
        if max_duration_seconds <= 0:
            raise ValueError("Die maximale Aufnahmedauer muss größer als null sein.")
        sd = self._module()
        import numpy as np

        capture_channels = self._resolve_capture_channels(input_index, channels)
        native_rate = self.resolve_input_sample_rate(input_index, sample_rate, capture_channels)
        self.last_input_stream_info = {"device_index": input_index, "requested_rate": int(sample_rate), "native_rate": int(native_rate), "channels": int(channels), "capture_channels": int(capture_channels)}
        target_frames = int(round(max_duration_seconds * native_rate))
        blocks: list[Any] = []
        captured = 0

        def callback(indata: Any, _frames: int, _time: Any, status: Any) -> None:
            nonlocal captured
            del status
            if stop_event.is_set() or captured >= target_frames:
                raise sd.CallbackStop
            remaining = target_frames - captured
            block = indata[:remaining].copy()
            blocks.append(block)
            captured += int(block.shape[0])
            if level_callback is not None and block.size:
                rms = float(np.sqrt(np.mean(np.square(block, dtype=np.float64))))
                level_callback(min(100.0, rms * 200.0))
            if stop_event.is_set() or captured >= target_frames:
                raise sd.CallbackStop

        with sd.InputStream(
            samplerate=native_rate, channels=channels, dtype="float32",
            device=input_index, callback=callback,
        ):
            while not stop_event.is_set() and captured < target_frames:
                sd.sleep(20)
        if not blocks:
            return np.empty((0, channels), dtype="float32")
        native = self._to_requested_channels(np.concatenate(blocks, axis=0)[:target_frames], channels)
        return self._resample(native, native_rate, sample_rate)


    def stream_input_blocks_until(
        self, *, input_index: int, stop_event: Event, max_duration_seconds: float,
        sample_rate: int, channels: int, block_callback: Callable[[Any], None],
        level_callback: Callable[[float], None] | None = None,
    ) -> None:
        """Öffnet das Gerät nativ und liefert einheitliche Zielraten-Blöcke."""
        sd = self._module()
        import numpy as np
        import time

        started = time.monotonic()
        capture_channels = self._resolve_capture_channels(input_index, channels)
        native_rate = self.resolve_input_sample_rate(input_index, sample_rate, capture_channels)
        device_info = sd.query_devices(input_index)
        host_api_name = ""
        try:
            host_api_name = str(sd.query_hostapis(int(device_info.get("hostapi", -1))).get("name", ""))
        except Exception:
            host_api_name = ""
        self.last_input_stream_info = {
            "device_index": input_index,
            "device_name": str(device_info.get("name", "")),
            "host_api": host_api_name,
            "requested_rate": int(sample_rate),
            "native_rate": int(native_rate),
            "channels": int(channels),
            "capture_channels": int(capture_channels),
            "default_rate": int(round(float(device_info.get("default_samplerate", native_rate)))),
            "max_input_channels": int(device_info.get("max_input_channels", capture_channels)),
            "default_low_input_latency": float(device_info.get("default_low_input_latency", 0.0)),
            "default_high_input_latency": float(device_info.get("default_high_input_latency", 0.0)),
            "dtype": "float32",
            "blocksize": 0,
            "callbacks": 0,
            "native_samples": 0,
            "status_messages": [],
            "channel_peak": [0.0 for _ in range(capture_channels)],
            "channel_rms": [0.0 for _ in range(capture_channels)],
            "active_channel": None,
        }
        pending: list[Any] = []
        pending_frames = 0
        flush_frames = max(1, int(round(native_rate * 0.2)))

        def emit_pending(force: bool = False) -> None:
            nonlocal pending, pending_frames
            if not pending or (not force and pending_frames < flush_frames):
                return
            native = self._to_requested_channels(np.concatenate(pending, axis=0), channels)
            converted = self._resample(native, native_rate, sample_rate)
            pending = []
            pending_frames = 0
            if converted.size:
                block_callback(converted)
                if level_callback is not None:
                    rms = float(np.sqrt(np.mean(np.square(converted, dtype=np.float64))))
                    level_callback(min(100.0, rms * 200.0))

        def callback(indata: Any, _frames: int, _time: Any, status: Any) -> None:
            nonlocal pending_frames
            if stop_event.is_set() or time.monotonic() - started >= max_duration_seconds:
                raise sd.CallbackStop
            block = np.asarray(indata, dtype=np.float32).copy()
            info = self.last_input_stream_info
            info["callbacks"] = int(info.get("callbacks", 0)) + 1
            if status:
                messages = list(info.get("status_messages") or [])
                text = str(status)
                if text and text not in messages:
                    messages.append(text)
                info["status_messages"] = messages[-10:]
            if block.size:
                if block.ndim == 1:
                    block = block.reshape(-1, 1)
                frames = int(block.shape[0])
                info["native_samples"] = int(info.get("native_samples", 0)) + frames
                for channel in range(min(capture_channels, block.shape[1])):
                    values = block[:, channel].astype(np.float64, copy=False)
                    peak = float(np.max(np.abs(values))) if values.size else 0.0
                    peaks = list(info.get("channel_peak") or [])
                    peaks[channel] = max(float(peaks[channel]), peak)
                    info["channel_peak"] = peaks
                    channel_sum_squares[channel] += float(np.sum(values * values))
                    channel_sample_counts[channel] += int(values.size)
                    rms_values = list(info.get("channel_rms") or [])
                    rms_values[channel] = float(np.sqrt(channel_sum_squares[channel] / max(1, channel_sample_counts[channel])))
                    info["channel_rms"] = rms_values
                peaks = list(info.get("channel_peak") or [])
                info["active_channel"] = int(max(range(len(peaks)), key=lambda idx: peaks[idx])) if peaks and max(peaks) > 0.0 else None
                pending.append(block)
                pending_frames += frames
                emit_pending()

        native_blocksize = max(1, int(round(native_rate * 0.02)))
        self.last_input_stream_info["blocksize"] = native_blocksize
        channel_sum_squares = np.zeros(capture_channels, dtype=np.float64)
        channel_sample_counts = np.zeros(capture_channels, dtype=np.int64)

        with sd.InputStream(
            samplerate=native_rate, channels=capture_channels, dtype="float32",
            device=input_index, callback=callback, blocksize=native_blocksize,
        ):
            while not stop_event.is_set() and time.monotonic() - started < max_duration_seconds:
                sd.sleep(10)
        emit_pending(force=True)

    def play_samples(
        self,
        samples: Any,
        *,
        output_index: int,
        sample_rate: int,
    ) -> None:
        sd = self._module()
        import numpy as np
        data = np.asarray(samples, dtype=np.float32)
        native_rate = self.resolve_output_sample_rate(output_index, sample_rate, 1)
        if native_rate != sample_rate:
            data = self._resample(data, sample_rate, native_rate)
        with sd.OutputStream(
            samplerate=native_rate, channels=1, dtype="float32",
            device=output_index, blocksize=max(1, int(round(native_rate * 0.02))),
        ) as stream:
            stream.write(data.reshape(-1, 1))

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
