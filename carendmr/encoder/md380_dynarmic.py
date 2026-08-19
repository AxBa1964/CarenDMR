"""ctypes-Zugriff auf den nativen MD380-Dynarmic-Vocoder."""
from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path

PCM_SAMPLES_PER_FRAME = 160
AMBE_BYTES_PER_FRAME = 9
MD380_INPUT_GAIN_DB = 2.0
MD380_INPUT_GAIN = 10.0 ** (MD380_INPUT_GAIN_DB / 20.0)


def default_md380_bridge_path(project_root: Path) -> Path:
    if os.name == "nt":
        name = "carendmr_md380_bridge.dll"
    elif sys.platform == "darwin":
        name = "libcarendmr_md380_bridge.dylib"
    else:
        name = "libcarendmr_md380_bridge.so"
    return project_root / "native" / name


class Md380DynarmicEncoder:
    def __init__(
        self,
        project_root: Path,
        library_path: Path | None = None,
        *,
        input_gain_db: float = MD380_INPUT_GAIN_DB,
    ) -> None:
        self._path = (library_path or default_md380_bridge_path(project_root)).resolve()
        self._input_gain_db = float(input_gain_db)
        self._input_gain = 10.0 ** (self._input_gain_db / 20.0)
        if not self._path.is_file():
            raise RuntimeError(f"MD380-Dynarmic-Bridge fehlt: {self._path}")

        self._dll_directory_handle = None
        if os.name == "nt" and hasattr(os, "add_dll_directory"):
            runtime_dir = Path(r"C:\msys64\ucrt64\bin")
            if runtime_dir.is_dir():
                self._dll_directory_handle = os.add_dll_directory(str(runtime_dir))

        try:
            self._lib = ctypes.CDLL(str(self._path))
        except OSError as error:
            if os.name == "nt":
                hint = (
                    " Unter Windows muss die MSYS2-UCRT64-Laufzeit verfügbar sein "
                    "(erwartet unter C:\\msys64\\ucrt64\\bin)."
                )
            else:
                hint = ""
            raise RuntimeError(
                "MD380-Dynarmic-Bridge konnte nicht geladen werden."
                f"{hint} Originalfehler: {error}"
            ) from error
        self._lib.carendmr_md380_init.argtypes = []
        self._lib.carendmr_md380_init.restype = ctypes.c_int
        self._lib.carendmr_md380_encode_fec.argtypes = [
            ctypes.POINTER(ctypes.c_int16), ctypes.POINTER(ctypes.c_uint8)
        ]
        self._lib.carendmr_md380_encode_fec.restype = ctypes.c_int
        self._lib.carendmr_md380_decode_fec.argtypes = [
            ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_int16)
        ]
        self._lib.carendmr_md380_decode_fec.restype = ctypes.c_int
        result = int(self._lib.carendmr_md380_init())
        if result != 0:
            raise RuntimeError(f"MD380-Dynarmic konnte nicht initialisiert werden (Code {result}).")

    @property
    def path(self) -> Path:
        return self._path

    def close(self) -> None:
        handle = self._dll_directory_handle
        self._dll_directory_handle = None
        if handle is not None:
            handle.close()

    def encode_2450x1150(self, pcm: tuple[int, ...]) -> bytes:
        if len(pcm) != PCM_SAMPLES_PER_FRAME:
            raise ValueError("Ein PCM-Frame muss genau 160 Samples enthalten.")
        # 0.2.1.25: +2 dB ist der Gewinner des kontrollierten MD380-Hörtests.
        # Ausschließlich der Eingang des MD380-Vocoders wird angehoben.
        adjusted = tuple(
            max(-32768, min(32767, int(round(sample * self._input_gain))))
            for sample in pcm
        )
        pcm_buf = (ctypes.c_int16 * PCM_SAMPLES_PER_FRAME)(*adjusted)
        ambe_buf = (ctypes.c_uint8 * AMBE_BYTES_PER_FRAME)()
        result = int(self._lib.carendmr_md380_encode_fec(pcm_buf, ambe_buf))
        if result != 0:
            raise RuntimeError(f"MD380-Encoding fehlgeschlagen (Code {result}).")
        return bytes(ambe_buf)

    def decode_2450x1150(self, ambe: bytes) -> tuple[int, ...]:
        """Dekodiert 9 Byte DMR-AMBE+2 mit md380_decode_fec."""
        if len(ambe) != AMBE_BYTES_PER_FRAME:
            raise ValueError("Ein AMBE-Frame muss genau 9 Bytes enthalten.")
        ambe_buf = (ctypes.c_uint8 * AMBE_BYTES_PER_FRAME).from_buffer_copy(ambe)
        pcm_buf = (ctypes.c_int16 * PCM_SAMPLES_PER_FRAME)()
        result = int(self._lib.carendmr_md380_decode_fec(ambe_buf, pcm_buf))
        if result != 0:
            raise RuntimeError(f"MD380-Decoding fehlgeschlagen (Code {result}).")
        return tuple(int(value) for value in pcm_buf)
