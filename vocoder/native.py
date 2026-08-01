"""ctypes bridge to CarenDMR's receive-only native mbelib helper."""

from __future__ import annotations

import ctypes
import platform
from pathlib import Path

from .base import (
    AMBE_CODEWORD_SIZE,
    PCM_SAMPLES_PER_CODEWORD,
    PcmFrame,
    VocoderDecodeError,
    VocoderUnavailableError,
)


def _default_library_path() -> Path:
    system = platform.system()

    if system == "Darwin":
        filename = "libcarendmr_mbe.dylib"
    elif system == "Windows":
        filename = "carendmr_mbe.dll"
    else:
        filename = "libcarendmr_mbe.so"

    return Path(__file__).resolve().parents[2] / "native" / filename


class NativeMbeReceiveVocoder:
    """Stateful AMBE+2 2450/1150 decoder; contains no encoding operation."""

    def __init__(self, library_path: str | Path | None = None) -> None:
        self._decoder: int | None = None
        path = Path(library_path) if library_path is not None else _default_library_path()
        try:
            self._library = ctypes.CDLL(str(path))
        except OSError as error:
            raise VocoderUnavailableError(
                "Der native DMR-Empfangsdecoder ist nicht verfügbar."
            ) from error

        byte_pointer = ctypes.POINTER(ctypes.c_uint8)
        sample_pointer = ctypes.POINTER(ctypes.c_int16)
        self._library.carendmr_mbe_decoder_create.restype = ctypes.c_void_p
        self._library.carendmr_mbe_decoder_destroy.argtypes = [ctypes.c_void_p]
        self._library.carendmr_mbe_decode.argtypes = [
            ctypes.c_void_p,
            byte_pointer,
            sample_pointer,
            ctypes.POINTER(ctypes.c_int),
        ]
        self._library.carendmr_mbe_decode.restype = ctypes.c_int
        self._decoder = self._library.carendmr_mbe_decoder_create()
        if not self._decoder:
            raise VocoderUnavailableError(
                "Der native DMR-Empfangsdecoder konnte nicht initialisiert werden."
            )

    def decode(self, codeword: bytes) -> PcmFrame:
        if not isinstance(codeword, bytes):
            raise TypeError("Ein AMBE-Codewort muss bytes sein.")
        if len(codeword) != AMBE_CODEWORD_SIZE:
            raise ValueError(
                f"Ein AMBE-Codewort muss genau {AMBE_CODEWORD_SIZE} Bytes lang sein."
            )
        if not self._decoder:
            raise VocoderDecodeError("Der DMR-Empfangsdecoder ist geschlossen.")

        encoded = (ctypes.c_uint8 * AMBE_CODEWORD_SIZE).from_buffer_copy(codeword)
        samples = (ctypes.c_int16 * PCM_SAMPLES_PER_CODEWORD)()
        errors = ctypes.c_int()
        result = self._library.carendmr_mbe_decode(
            self._decoder,
            encoded,
            samples,
            ctypes.byref(errors),
        )
        if result != 0:
            raise VocoderDecodeError(
                f"Der native DMR-Empfangsdecoder meldete Fehler {result}."
            )
        return PcmFrame(tuple(samples), errors.value)

    def close(self) -> None:
        if self._decoder:
            self._library.carendmr_mbe_decoder_destroy(self._decoder)
            self._decoder = None

    def __enter__(self) -> "NativeMbeReceiveVocoder":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def __del__(self) -> None:
        self.close()
