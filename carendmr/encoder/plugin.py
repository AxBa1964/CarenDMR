"""DroidStar-kompatibles Vocoder-Plugin über eine kleine native C++-Bridge."""

from __future__ import annotations

import ctypes
import json
import platform
from pathlib import Path

from .base import (
    AMBE_BYTES_PER_FRAME,
    PCM_SAMPLES_PER_FRAME,
    AmbeEncoder,
    EncoderDiagnostics,
    EncoderUnavailableError,
    EncoderValidationError,
)


def default_bridge_path(project_root: Path) -> Path:
    system = platform.system()
    if system == "Windows":
        name = "carendmr_vocoder_bridge.dll"
    elif system == "Darwin":
        name = "libcarendmr_vocoder_bridge.dylib"
    else:
        name = "libcarendmr_vocoder_bridge.so"
    return Path(project_root) / "native" / name


class DroidStarPluginEncoder(AmbeEncoder):
    """Lädt ein separat bereitgestelltes DroidStar-Vocoder-Plugin."""

    def __init__(self, project_root: Path, plugin_path: str | Path) -> None:
        self.project_root = Path(project_root)
        self.plugin_path = Path(plugin_path).expanduser().resolve()
        self.bridge_path = default_bridge_path(self.project_root)
        self._handle: int | None = None

        if not self.plugin_path.is_file():
            raise EncoderUnavailableError("Die ausgewählte Vocoder-Plugin-Datei existiert nicht.")
        if not self.bridge_path.is_file():
            raise EncoderUnavailableError(
                "Die native CarenDMR-Vocoder-Bridge ist nicht gebaut. "
                "Bitte den Build-Schritt aus DEPLOY.md ausführen."
            )
        try:
            self._library = ctypes.CDLL(str(self.bridge_path))
        except OSError as error:
            raise EncoderUnavailableError(
                f"Die Vocoder-Bridge konnte nicht geladen werden: {error}"
            ) from error

        self._library.carendmr_vocoder_open.argtypes = [ctypes.c_char_p]
        self._library.carendmr_vocoder_open.restype = ctypes.c_void_p
        self._library.carendmr_vocoder_close.argtypes = [ctypes.c_void_p]
        self._library.carendmr_vocoder_close.restype = None
        self._library.carendmr_vocoder_encode_2450x1150.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_int16),
            ctypes.POINTER(ctypes.c_uint8),
        ]
        self._library.carendmr_vocoder_encode_2450x1150.restype = ctypes.c_int
        self._library.carendmr_vocoder_last_error.argtypes = []
        self._library.carendmr_vocoder_last_error.restype = ctypes.c_char_p

        path_bytes = str(self.plugin_path).encode("utf-8")
        self._handle = int(self._library.carendmr_vocoder_open(path_bytes) or 0)
        if not self._handle:
            raise EncoderUnavailableError(self._last_error())

    def _last_error(self) -> str:
        raw = self._library.carendmr_vocoder_last_error()
        if not raw:
            return "Das DroidStar-Vocoder-Plugin konnte nicht initialisiert werden."
        return raw.decode("utf-8", errors="replace")

    def encode_2450x1150(self, pcm_samples: tuple[int, ...]) -> bytes:
        if len(pcm_samples) != PCM_SAMPLES_PER_FRAME:
            raise ValueError(
                f"Ein Encoderrahmen benötigt exakt {PCM_SAMPLES_PER_FRAME} PCM-Samples."
            )
        if not self._handle:
            raise EncoderUnavailableError("Der AMBE-Encoder ist geschlossen.")
        pcm = (ctypes.c_int16 * PCM_SAMPLES_PER_FRAME)(*pcm_samples)
        output = (ctypes.c_uint8 * AMBE_BYTES_PER_FRAME)()
        result = self._library.carendmr_vocoder_encode_2450x1150(
            ctypes.c_void_p(self._handle), pcm, output
        )
        if result != 0:
            raise EncoderValidationError(self._last_error())
        encoded = bytes(output)
        if len(encoded) != AMBE_BYTES_PER_FRAME:
            raise EncoderValidationError("Das Plugin lieferte keinen 72-Bit-AMBE-Rahmen.")
        return encoded

    def close(self) -> None:
        if self._handle:
            self._library.carendmr_vocoder_close(ctypes.c_void_p(self._handle))
            self._handle = None

    def __enter__(self) -> "DroidStarPluginEncoder":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass


class EncoderSettingsStore:
    """Speichert ausschließlich den lokalen Pluginpfad; niemals das Plugin selbst."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def load_plugin_path(self) -> Path | None:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            value = payload.get("droidstar_plugin_path", "")
            return Path(value) if isinstance(value, str) and value.strip() else None
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return None

    def save_plugin_path(self, plugin_path: Path) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"droidstar_plugin_path": str(Path(plugin_path).resolve())}
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def verify_plugin(project_root: Path, plugin_path: Path) -> EncoderDiagnostics:
    """Führt einen rein lokalen deterministischen PCM→AMBE-Test aus."""
    silence = (0,) * PCM_SAMPLES_PER_FRAME
    with DroidStarPluginEncoder(project_root, plugin_path) as encoder:
        encoded = encoder.encode_2450x1150(silence)
    return EncoderDiagnostics(
        backend="DroidStar-kompatibles Plugin",
        plugin_path=str(Path(plugin_path).resolve()),
        ready=True,
        encoded_bytes=len(encoded),
        message="Offline-PCM-zu-AMBE-Test erfolgreich; es wurde nichts gesendet.",
    )
