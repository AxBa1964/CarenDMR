"""Produktiver MD380-Dynarmic-Empfangsdecoder für DMR AMBE+2 2450/1150."""

from __future__ import annotations

import ctypes
import os
from pathlib import Path

from carendmr.encoder.md380_dynarmic import (
    AMBE_BYTES_PER_FRAME,
    PCM_SAMPLES_PER_FRAME,
    default_md380_bridge_path,
)
from .base import PcmFrame, VocoderDecodeError, VocoderUnavailableError


class Md380DynarmicReceiveVocoder:
    """Direkter md380_decode_fec-Pfad wie in DroidStar."""

    def __init__(self, project_root: Path, library_path: Path | None = None) -> None:
        self._path = (library_path or default_md380_bridge_path(project_root)).resolve()
        if not self._path.is_file():
            raise VocoderUnavailableError(
                f"MD380-Dynarmic-RX-Bridge fehlt: {self._path}"
            )

        self._dll_directory_handle = None
        if os.name == "nt" and hasattr(os, "add_dll_directory"):
            runtime_dir = Path(r"C:\msys64\ucrt64\bin")
            if runtime_dir.is_dir():
                self._dll_directory_handle = os.add_dll_directory(str(runtime_dir))

        try:
            self._lib = ctypes.CDLL(str(self._path))
        except OSError as error:
            raise VocoderUnavailableError(
                f"MD380-Dynarmic-RX-Bridge konnte nicht geladen werden: {error}"
            ) from error

        self._lib.carendmr_md380_init.argtypes = []
        self._lib.carendmr_md380_init.restype = ctypes.c_int
        self._lib.carendmr_md380_decode_fec.argtypes = [
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.POINTER(ctypes.c_int16),
        ]
        self._lib.carendmr_md380_decode_fec.restype = ctypes.c_int

        result = int(self._lib.carendmr_md380_init())
        if result != 0:
            raise VocoderUnavailableError(
                f"MD380-Dynarmic konnte nicht initialisiert werden (Code {result})."
            )
        self._closed = False

    @property
    def path(self) -> Path:
        return self._path

    def decode(self, codeword: bytes) -> PcmFrame:
        if self._closed:
            raise VocoderDecodeError("Der MD380-RX-Decoder ist geschlossen.")
        if not isinstance(codeword, bytes):
            raise TypeError("Ein AMBE-Codewort muss bytes sein.")
        if len(codeword) != AMBE_BYTES_PER_FRAME:
            raise ValueError(
                f"Ein AMBE-Codewort muss genau {AMBE_BYTES_PER_FRAME} Bytes lang sein."
            )

        ambe_buf = (ctypes.c_uint8 * AMBE_BYTES_PER_FRAME).from_buffer_copy(codeword)
        pcm_buf = (ctypes.c_int16 * PCM_SAMPLES_PER_FRAME)()
        result = int(self._lib.carendmr_md380_decode_fec(ambe_buf, pcm_buf))
        if result != 0:
            raise VocoderDecodeError(
                f"MD380-Decoding fehlgeschlagen (Code {result})."
            )
        # md380_decode_fec liefert für diesen direkten Softwarepfad keine
        # separate korrigierte-Fehlerzahl. 0 bedeutet hier: API meldete Erfolg.
        return PcmFrame(tuple(int(value) for value in pcm_buf), 0)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        handle = self._dll_directory_handle
        self._dll_directory_handle = None
        if handle is not None:
            handle.close()

    def __enter__(self) -> "Md380DynarmicReceiveVocoder":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass
