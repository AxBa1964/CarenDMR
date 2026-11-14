"""Einrichtung des Sprach-Codecs (MD380-Firmware zur Laufzeit).

Ab 0.2.1.88 bereitet CarenDMR vor, dass die MD380-Firmware nicht mehr in die
Bridge-DLL eingebaut ist, sondern vom Nutzer bereitgestellt und beim Start
geladen wird (Variante B, wie VoxDMR und greyfoxsolid/vocoder).

Der Dienst kennt zwei Bridge-Arten:

* **alte Bridge** – Firmware ist eingebaut; Export ``carendmr_md380_init``.
  Es sind keine Dateien nötig.
* **neue Bridge** – Firmware wird geladen; zusätzlicher Export
  ``carendmr_md380_init_files(firmware_path, core_path)``. Dann müssen die
  beiden Dateien im Firmware-Ordner des Datenordners liegen.

Der Dienst ist Qt-frei; Oberflächen zeigen nur ``CodecReport.message`` an.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from carendmr.app_paths import firmware_dir
from carendmr.encoder.md380_dynarmic import default_md380_bridge_path

FIRMWARE_FILE = "D002.032.bin"
CORE_FILE = "d02032-core.img"
RUNTIME_INIT_SYMBOL = b"carendmr_md380_init_files"
MANIFEST_FILE = "codec_manifest.json"

# Kopf verpackter (verschlüsselter) Tytera-Update-Dateien, laut md380tools.
WRAPPED_MAGIC = b"OutSecurityBin"
# Die Firmware liegt ab 0x0800C000 im 1-MiB-Flash des STM32F405;
# das ausgepackte Abbild kann daher höchstens 0xF4000 Bytes groß sein.
MAX_FIRMWARE_BYTES = 0x100000 - 0xC000

SETUP_HINT = (
    "Die Einrichtung erscheint beim nächsten Programmstart oder im Hauptfenster "
    "unter Programm, Sprach-Codec einrichten."
)


class CodecState(str, Enum):
    READY_EMBEDDED = "ready_embedded"
    READY_FILES = "ready_files"
    FILES_MISSING = "files_missing"
    BRIDGE_MISSING = "bridge_missing"


@dataclass(frozen=True, slots=True)
class CodecReport:
    state: CodecState
    message: str
    bridge_path: Path
    firmware_path: Path
    core_path: Path

    @property
    def ready(self) -> bool:
        return self.state in (CodecState.READY_EMBEDDED, CodecState.READY_FILES)


class CodecSetupError(ValueError):
    """Eine ausgewählte Datei ist für den Codec nicht geeignet."""


def bridge_loads_firmware_at_runtime(bridge_path: Path) -> bool:
    """Erkennt die neue Bridge am Exportnamen, ohne die DLL zu laden."""
    try:
        data = Path(bridge_path).read_bytes()
    except OSError:
        return False
    return RUNTIME_INIT_SYMBOL in data


def codec_file_paths(project_root: Path) -> tuple[Path, Path]:
    folder = firmware_dir(project_root)
    return folder / FIRMWARE_FILE, folder / CORE_FILE


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_firmware_file(path: Path) -> None:
    path = Path(path)
    if not path.is_file():
        raise CodecSetupError(f"Die Firmware-Datei wurde nicht gefunden: {path}")
    size = path.stat().st_size
    if size == 0:
        raise CodecSetupError("Die Firmware-Datei ist leer.")
    with path.open("rb") as handle:
        head = handle.read(256)
    if head.startswith(WRAPPED_MAGIC):
        raise CodecSetupError(
            "Das ist eine verpackte Tytera-Update-Datei. Benötigt wird die "
            f"ausgepackte Firmware {FIRMWARE_FILE}."
        )
    if size > MAX_FIRMWARE_BYTES:
        raise CodecSetupError(
            "Die Firmware-Datei ist zu groß für ein MD380-Firmware-Abbild."
        )


def validate_core_file(path: Path) -> None:
    path = Path(path)
    if not path.is_file():
        raise CodecSetupError(f"Das RAM-Abbild wurde nicht gefunden: {path}")
    size = path.stat().st_size
    if size == 0:
        raise CodecSetupError("Das RAM-Abbild ist leer.")


class CodecSetupService:
    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root)

    @property
    def bridge_path(self) -> Path:
        return default_md380_bridge_path(self.project_root)

    @property
    def firmware_path(self) -> Path:
        return codec_file_paths(self.project_root)[0]

    @property
    def core_path(self) -> Path:
        return codec_file_paths(self.project_root)[1]

    def _report(self, state: CodecState, message: str) -> CodecReport:
        return CodecReport(state, message, self.bridge_path, self.firmware_path, self.core_path)

    def status(self) -> CodecReport:
        if not self.bridge_path.is_file():
            return self._report(
                CodecState.BRIDGE_MISSING,
                "Der Sprach-Codec ist nicht installiert: Die MD380-Bridge fehlt. "
                "Senden und Empfangen sind nicht möglich.",
            )
        if not bridge_loads_firmware_at_runtime(self.bridge_path):
            return self._report(CodecState.READY_EMBEDDED, "Der Sprach-Codec ist bereit.")
        missing = [
            name
            for name, path in ((FIRMWARE_FILE, self.firmware_path), (CORE_FILE, self.core_path))
            if not path.is_file()
        ]
        if missing:
            return self._report(
                CodecState.FILES_MISSING,
                "Der Sprach-Codec ist noch nicht eingerichtet. Es fehlen: "
                + ", ".join(missing)
                + ". Senden und Empfangen sind erst danach möglich. "
                + SETUP_HINT,
            )
        return self._report(CodecState.READY_FILES, "Der Sprach-Codec ist bereit.")

    def install_files(self, firmware_source: Path, core_source: Path) -> CodecReport:
        """Prüft beide Dateien und kopiert sie in den Firmware-Ordner."""
        firmware_source = Path(firmware_source)
        core_source = Path(core_source)
        validate_firmware_file(firmware_source)
        validate_core_file(core_source)

        folder = firmware_dir(self.project_root)
        folder.mkdir(parents=True, exist_ok=True)
        for source, target in ((firmware_source, self.firmware_path), (core_source, self.core_path)):
            try:
                same = source.resolve() == target.resolve()
            except OSError:
                same = False
            if same:
                continue
            temporary = target.with_suffix(target.suffix + ".tmp")
            shutil.copyfile(source, temporary)
            temporary.replace(target)

        manifest = {
            "installed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "firmware": {"file": FIRMWARE_FILE, "sha256": _sha256(self.firmware_path)},
            "core": {"file": CORE_FILE, "sha256": _sha256(self.core_path)},
        }
        (folder / MANIFEST_FILE).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return self.status()

    def remove_files(self) -> CodecReport:
        for path in (self.firmware_path, self.core_path, firmware_dir(self.project_root) / MANIFEST_FILE):
            if path.is_file():
                path.unlink()
        return self.status()
