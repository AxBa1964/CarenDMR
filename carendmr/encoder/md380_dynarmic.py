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
    from carendmr.app_paths import native_dir
    return native_dir(project_root) / name


def initialize_md380(lib, project_root: Path) -> int:
    """Initialisiert die Bridge; neue Bridges laden die Firmware aus Dateien.

    Ab 0.2.1.88 vorbereitet: Bietet die Bridge ``carendmr_md380_init_files``,
    werden ``D002.032.bin`` und ``d02032-core.img`` aus dem Firmware-Ordner
    des Datenordners übergeben. Ältere Bridges mit eingebauter Firmware
    werden unverändert über ``carendmr_md380_init`` gestartet.
    """
    init_files = getattr(lib, "carendmr_md380_init_files", None)
    if init_files is None:
        lib.carendmr_md380_init.argtypes = []
        lib.carendmr_md380_init.restype = ctypes.c_int
        return int(lib.carendmr_md380_init())

    from carendmr.application.codec_setup_service import SETUP_HINT, codec_file_paths

    firmware, core = codec_file_paths(project_root)
    missing = [path.name for path in (firmware, core) if not path.is_file()]
    if missing:
        raise RuntimeError(
            "Der Sprach-Codec ist noch nicht eingerichtet (es fehlen: "
            + ", ".join(missing)
            + "). "
            + SETUP_HINT
        )
    init_files.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    init_files.restype = ctypes.c_int
    # Die Bridge erwartet UTF-8-Pfade (unter Windows per _wfopen geöffnet).
    result = int(init_files(str(firmware).encode("utf-8"), str(core).encode("utf-8")))
    if result != 0:
        detail = ""
        last_error = getattr(lib, "carendmr_md380_last_error", None)
        if last_error is not None:
            last_error.argtypes = []
            last_error.restype = ctypes.c_char_p
            raw = last_error()
            if raw:
                detail = " " + raw.decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Der Sprach-Codec konnte nicht gestartet werden (Code {result}).{detail} "
            + SETUP_HINT
        )
    return result


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
        self._native_dll_handle = None
        if os.name == "nt" and hasattr(os, "add_dll_directory"):
            runtime_dir = Path(r"C:\msys64\ucrt64\bin")
            if runtime_dir.is_dir():
                self._dll_directory_handle = os.add_dll_directory(str(runtime_dir))
            # 0.2.1.88: In der Exe liegen die Laufzeit-DLLs (libstdc++ usw.)
            # neben der Bridge; ohne MSYS2 muss dieser Ordner reichen.
            self._native_dll_handle = os.add_dll_directory(str(self._path.parent))

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
        self._lib.carendmr_md380_encode_fec.argtypes = [
            ctypes.POINTER(ctypes.c_int16), ctypes.POINTER(ctypes.c_uint8)
        ]
        self._lib.carendmr_md380_encode_fec.restype = ctypes.c_int
        self._lib.carendmr_md380_decode_fec.argtypes = [
            ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_int16)
        ]
        self._lib.carendmr_md380_decode_fec.restype = ctypes.c_int
        result = initialize_md380(self._lib, project_root)
        if result != 0:
            raise RuntimeError(f"MD380-Dynarmic konnte nicht initialisiert werden (Code {result}).")

    @property
    def path(self) -> Path:
        return self._path

    def close(self) -> None:
        for name in ("_dll_directory_handle", "_native_dll_handle"):
            handle = getattr(self, name, None)
            setattr(self, name, None)
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
