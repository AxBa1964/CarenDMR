"""Opus-Codec über die Systembibliothek libopus (ctypes, ohne Zusatzpaket).

Fundorte der Bibliothek:
- Windows: ``native\\libopus-0.dll`` bzw. ``native\\opus.dll`` im Programmordner,
  sonst MSYS2 UCRT64 (``C:\\msys64\\ucrt64\\bin\\libopus-0.dll``, Paket
  ``mingw-w64-ucrt-x86_64-opus``).
- Linux/Raspberry Pi: ``libopus.so.0`` (Paket ``libopus0``).
- macOS: ``libopus.dylib`` (Homebrew ``opus``).
"""
from __future__ import annotations

import ctypes
import ctypes.util
import os
import sys
from pathlib import Path

OPUS_OK = 0
OPUS_APPLICATION_VOIP = 2048
MAX_FRAME_SAMPLES_16K = 16000 * 120 // 1000  # längster Opus-Rahmen (120 ms)


class OpusUnavailableError(RuntimeError):
    """libopus ist nicht installiert oder nicht ladbar."""


class OpusError(RuntimeError):
    """Kodieren oder Dekodieren ist fehlgeschlagen."""


INSTALL_HINT = (
    "Opus fehlt. Raspberry Pi/Linux: sudo apt install libopus0. "
    "Windows (MSYS2 UCRT64): pacman -S mingw-w64-ucrt-x86_64-opus. "
    "macOS: brew install opus."
)


def _candidates(native_dir: Path | None) -> list[str]:
    names: list[str] = []
    if os.name == "nt":
        folders = [native_dir] if native_dir else []
        folders.append(Path(r"C:\msys64\ucrt64\bin"))
        for folder in folders:
            for name in ("libopus-0.dll", "opus.dll"):
                path = folder / name
                if path.is_file():
                    names.append(str(path))
    elif native_dir is not None:
        for name in ("libopus.so.0", "libopus.dylib"):
            path = native_dir / name
            if path.is_file():
                names.append(str(path))
    found = ctypes.util.find_library("opus")
    if found:
        names.append(found)
    if sys.platform == "darwin":
        names += ["/usr/local/lib/libopus.dylib", "/opt/homebrew/lib/libopus.dylib"]
    elif os.name != "nt":
        names.append("libopus.so.0")
    return names


def load_libopus(native_dir: Path | None = None):
    errors: list[str] = []
    for candidate in _candidates(native_dir):
        try:
            lib = ctypes.CDLL(candidate)
        except OSError as error:
            errors.append(f"{candidate}: {error}")
            continue
        _declare(lib)
        return lib
    detail = f" ({'; '.join(errors)})" if errors else ""
    raise OpusUnavailableError(INSTALL_HINT + detail)


def _declare(lib) -> None:
    lib.opus_decoder_create.argtypes = [ctypes.c_int32, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
    lib.opus_decoder_create.restype = ctypes.c_void_p
    lib.opus_decode.argtypes = [
        ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int32,
        ctypes.POINTER(ctypes.c_int16), ctypes.c_int, ctypes.c_int,
    ]
    lib.opus_decode.restype = ctypes.c_int
    lib.opus_decoder_destroy.argtypes = [ctypes.c_void_p]
    lib.opus_decoder_destroy.restype = None
    lib.opus_encoder_create.argtypes = [ctypes.c_int32, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
    lib.opus_encoder_create.restype = ctypes.c_void_p
    lib.opus_encode.argtypes = [
        ctypes.c_void_p, ctypes.POINTER(ctypes.c_int16), ctypes.c_int,
        ctypes.c_char_p, ctypes.c_int32,
    ]
    lib.opus_encode.restype = ctypes.c_int32
    lib.opus_encoder_destroy.argtypes = [ctypes.c_void_p]
    lib.opus_encoder_destroy.restype = None


class OpusDecoder:
    """Mono-Decoder; liefert PCM16-Werte."""

    def __init__(self, sample_rate: int = 16000, *, lib=None, native_dir: Path | None = None) -> None:
        self._lib = lib or load_libopus(native_dir)
        error = ctypes.c_int(0)
        self._state = self._lib.opus_decoder_create(sample_rate, 1, ctypes.byref(error))
        if not self._state or error.value != OPUS_OK:
            raise OpusError(f"Opus-Decoder konnte nicht angelegt werden (Code {error.value}).")
        self._max = sample_rate * 120 // 1000
        self._last_frame = sample_rate * 20 // 1000
        self._buffer = (ctypes.c_int16 * self._max)()

    def decode(self, packet: bytes | None) -> tuple[int, ...]:
        """Dekodiert ein Paket; ``None`` = verlorenes Paket (Verschleierung)."""
        if self._state is None:
            raise OpusError("Der Opus-Decoder ist geschlossen.")
        if packet:
            count = self._lib.opus_decode(self._state, packet, len(packet), self._buffer, self._max, 0)
        else:
            # Verschleierung: Länge muss der erwarteten Rahmenlänge entsprechen.
            count = self._lib.opus_decode(self._state, None, 0, self._buffer, self._last_frame, 0)
        if count < 0:
            raise OpusError(f"Opus-Dekodierung fehlgeschlagen (Code {count}).")
        if packet:
            self._last_frame = count
        return tuple(self._buffer[:count])

    def close(self) -> None:
        if self._state is not None:
            self._lib.opus_decoder_destroy(self._state)
            self._state = None

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass


class OpusEncoder:
    """Mono-Encoder (für Tests und den späteren Sendeweg)."""

    def __init__(self, sample_rate: int = 16000, *, lib=None, native_dir: Path | None = None) -> None:
        self._lib = lib or load_libopus(native_dir)
        error = ctypes.c_int(0)
        self._state = self._lib.opus_encoder_create(
            sample_rate, 1, OPUS_APPLICATION_VOIP, ctypes.byref(error)
        )
        if not self._state or error.value != OPUS_OK:
            raise OpusError(f"Opus-Encoder konnte nicht angelegt werden (Code {error.value}).")
        self._out = ctypes.create_string_buffer(4000)

    def encode(self, pcm: tuple[int, ...] | list[int]) -> bytes:
        if self._state is None:
            raise OpusError("Der Opus-Encoder ist geschlossen.")
        samples = (ctypes.c_int16 * len(pcm))(*pcm)
        size = self._lib.opus_encode(self._state, samples, len(pcm), self._out, len(self._out))
        if size < 0:
            raise OpusError(f"Opus-Kodierung fehlgeschlagen (Code {size}).")
        return self._out.raw[:size]

    def close(self) -> None:
        if self._state is not None:
            self._lib.opus_encoder_destroy(self._state)
            self._state = None

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass
