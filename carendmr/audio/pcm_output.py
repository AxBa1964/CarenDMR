"""Bounded callback-driven mono PCM output for live receive audio."""

from __future__ import annotations

import math
import struct
import threading
from typing import Any, Callable, Iterable


class PcmOutputError(RuntimeError):
    """The default output device cannot provide the requested PCM stream."""


class BufferedPcmOutput:
    """Thread-safe 8 kHz signed-16-bit mono output with gain, AGC and limiting."""

    def __init__(
        self,
        *,
        sample_rate: int = 8000,
        maximum_buffer_seconds: float = 2.0,
        sounddevice_module: Any | None = None,
        muted: Callable[[], bool] | None = None,
        volume: Callable[[], float] | None = None,
        agc_enabled: Callable[[], bool] | None = None,
        level_callback: Callable[[float], None] | None = None,
    ) -> None:
        if sample_rate <= 0 or maximum_buffer_seconds <= 0:
            raise ValueError("Audio rate and buffer duration must be positive.")
        self.sample_rate = sample_rate
        self._maximum_bytes = int(sample_rate * maximum_buffer_seconds * 2)
        self._sd = sounddevice_module
        self._muted = muted or (lambda: False)
        self._volume = volume or (lambda: 1.0)
        self._agc_enabled = agc_enabled or (lambda: False)
        self._level_callback = level_callback
        self._stream: Any | None = None
        self._buffer = bytearray()
        self._lock = threading.Lock()
        self._agc_gain = 1.0
        self.samples_written = 0
        self.samples_played = 0
        self.underrun_callbacks = 0
        self.dropped_samples = 0

    @property
    def is_open(self) -> bool:
        return self._stream is not None

    def _module(self) -> Any:
        if self._sd is None:
            try:
                import sounddevice as sd
            except ImportError as error:
                raise PcmOutputError(
                    "Die Audio-Bibliothek sounddevice ist nicht verfügbar."
                ) from error
            self._sd = sd
        return self._sd

    def start(self) -> None:
        if self._stream is not None:
            return
        sd = self._module()
        try:
            default = sd.query_devices(kind="output")
            if int(default["max_output_channels"]) < 1:
                raise PcmOutputError(
                    "Das Standard-Wiedergabegerät besitzt keinen Ausgabekanal."
                )
            self._stream = sd.RawOutputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                callback=self._callback,
                blocksize=160,
            )
            self._stream.start()
        except PcmOutputError:
            self._stream = None
            raise
        except Exception as error:
            self._stream = None
            raise PcmOutputError(
                "Das Standard-Wiedergabegerät konnte nicht geöffnet werden."
            ) from error

    def write(self, samples: Iterable[int]) -> None:
        values = tuple(samples)
        if not values:
            return
        if any(not -32768 <= value <= 32767 for value in values):
            raise ValueError("PCM-Samples müssen signed 16 bit sein.")
        encoded = struct.pack(f"<{len(values)}h", *values)
        with self._lock:
            excess = len(self._buffer) + len(encoded) - self._maximum_bytes
            if excess > 0:
                drop = min(len(self._buffer), excess + (excess % 2))
                del self._buffer[:drop]
                self.dropped_samples += drop // 2
            self._buffer.extend(encoded)
            self.samples_written += len(values)

    @staticmethod
    def _soft_limit(value: float) -> int:
        # Smoothly limits large values while preserving speech detail below clipping.
        normalized = value / 32767.0
        limited = math.tanh(normalized) * 32767.0
        return max(-32768, min(32767, int(round(limited))))

    def _apply_agc(self, values: tuple[int, ...]) -> tuple[int, ...]:
        if not values or not self._agc_enabled():
            self._agc_gain += (1.0 - self._agc_gain) * 0.05
            return values
        rms = math.sqrt(sum(float(v) * float(v) for v in values) / len(values))
        if rms < 80.0:
            target_gain = self._agc_gain
        else:
            target_rms = 6500.0
            target_gain = max(0.35, min(4.0, target_rms / rms))
        # Slow attack/release avoids audible pumping between syllables.
        rate = 0.08 if target_gain < self._agc_gain else 0.025
        self._agc_gain += (target_gain - self._agc_gain) * rate
        return tuple(int(round(v * self._agc_gain)) for v in values)

    def _callback(
        self,
        outdata: memoryview,
        frames: int,
        _time: object,
        _status: object,
    ) -> None:
        required = frames * 2
        if self._muted():
            with self._lock:
                self._buffer.clear()
            outdata[:required] = bytes(required)
            self.samples_played += frames
            if self._level_callback is not None:
                self._level_callback(0.0)
            return
        with self._lock:
            available = min(required, len(self._buffer))
            chunk = bytes(self._buffer[:available])
            del self._buffer[:available]
        if chunk:
            values = struct.unpack(f"<{len(chunk) // 2}h", chunk)
            values = self._apply_agc(values)
            factor = max(0.0, min(4.0, float(self._volume())))
            processed = tuple(self._soft_limit(v * factor) for v in values)
            peak = max(abs(v) for v in processed) / 32767.0 * 100.0 if processed else 0.0
            if self._level_callback is not None:
                self._level_callback(max(0.0, min(100.0, peak)))
            chunk = struct.pack(f"<{len(processed)}h", *processed)
        outdata[:available] = chunk
        if available < required:
            outdata[available:required] = bytes(required - available)
            self.underrun_callbacks += 1
        self.samples_played += frames

    def close(self) -> None:
        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                stream.stop()
            finally:
                stream.close()
        with self._lock:
            self._buffer.clear()

    def __enter__(self) -> "BufferedPcmOutput":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
