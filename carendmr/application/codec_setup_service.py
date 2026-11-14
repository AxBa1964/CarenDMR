"""Einrichtung des Sprach-Codecs (MD380-Firmware zur Laufzeit).

Ab 0.2.1.89 ist die MD380-Firmware nicht mehr in die Bridge-DLL eingebaut.
Der Nutzer lädt sie über diesen Dienst herunter oder wählt eigene Dateien;
die Bridge lädt sie beim Start (wie VoxDMR und greyfoxsolid/vocoder).

Der Dienst kennt zwei Bridge-Arten:

* **alte Bridge** – Firmware ist eingebaut; Export ``carendmr_md380_init``.
  Es sind keine Dateien nötig.
* **neue Bridge** – Firmware wird geladen; zusätzlicher Export
  ``carendmr_md380_init_files(firmware_path, core_path)``. Dann müssen die
  beiden Dateien im Firmware-Ordner des Datenordners liegen.

Der Dienst ist Qt-frei; Oberflächen zeigen nur ``CodecReport.message`` an.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from carendmr.app_paths import firmware_dir
from carendmr.encoder.md380_dynarmic import default_md380_bridge_path
from carendmr.vocoder import md380_firmware

FIRMWARE_FILE = "D002.032.bin"
CORE_FILE = "d02032-core.img"
RUNTIME_INIT_SYMBOL = b"carendmr_md380_init_files"
MANIFEST_FILE = "codec_manifest.json"

DOWNLOAD_TIMEOUT_SECONDS = 30
MAX_DOWNLOAD_BYTES = 20 * 1024 * 1024

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


def _read(path: Path, what: str) -> bytes:
    path = Path(path)
    if not path.is_file():
        raise CodecSetupError(f"{what} wurde nicht gefunden: {path}")
    if path.stat().st_size > MAX_DOWNLOAD_BYTES:
        raise CodecSetupError(f"{what} ist viel zu groß.")
    return path.read_bytes()


def _download(url: str, label: str) -> bytes:
    import ssl
    import urllib.error
    import urllib.request

    try:
        import certifi

        context = ssl.create_default_context(cafile=certifi.where())
    except ImportError:  # pragma: no cover - certifi ist in requirements.txt
        context = ssl.create_default_context()
    request = urllib.request.Request(url, headers={"User-Agent": "CarenDMR"})
    try:
        with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT_SECONDS, context=context) as response:
            data = response.read(MAX_DOWNLOAD_BYTES + 1)
    except (urllib.error.URLError, OSError) as error:
        raise CodecSetupError(
            f"{label} konnte nicht heruntergeladen werden ({error}). "
            "Bitte Internetverbindung prüfen oder die Dateien selbst auswählen."
        ) from error
    if len(data) > MAX_DOWNLOAD_BYTES:
        raise CodecSetupError(f"{label}: Download ist unerwartet groß und wurde verworfen.")
    return data


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
        """Übernimmt vom Nutzer gewählte Dateien.

        Firmware: Original-ZIP, verpackte Update-Datei oder D002.032.bin.
        RAM-Abbild: d02032-core.img (Prüfsumme muss stimmen).
        """
        firmware_data = _read(firmware_source, "Die Firmware-Datei")
        core_data = _read(core_source, "Das RAM-Abbild")
        return self.install_bytes(firmware_data, core_data, source="Dateiauswahl")

    def download_and_install(self, progress=None) -> CodecReport:
        """Lädt Firmware (md380.org) und RAM-Abbild (md380tools) und richtet sie ein.

        ``progress`` erhält kurze deutsche Statustexte für die Ansage.
        """
        def say(text: str) -> None:
            if progress is not None:
                progress(text)

        say("Firmware wird von md380.org geladen.")
        firmware_data = _download(md380_firmware.FIRMWARE_ZIP_URL, "Die Firmware")
        say("RAM-Abbild wird von md380tools geladen.")
        core_data = _download(md380_firmware.CORE_URL, "Das RAM-Abbild")
        say("Dateien werden geprüft und eingerichtet.")
        return self.install_bytes(firmware_data, core_data, source="Download")

    def install_bytes(self, firmware_data: bytes, core_data: bytes, *, source: str) -> CodecReport:
        try:
            firmware_image, origin = md380_firmware.firmware_from_bytes(firmware_data)
            md380_firmware.check_core(core_data)
        except md380_firmware.FirmwareFormatError as error:
            raise CodecSetupError(str(error)) from error

        folder = firmware_dir(self.project_root)
        folder.mkdir(parents=True, exist_ok=True)
        for data, target in ((firmware_image, self.firmware_path), (core_data, self.core_path)):
            temporary = target.with_suffix(target.suffix + ".tmp")
            temporary.write_bytes(data)
            temporary.replace(target)

        manifest = {
            "installed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": source,
            "firmware": {
                "file": FIRMWARE_FILE,
                "sha256": md380_firmware.sha256(firmware_image),
                "check": origin,
            },
            "core": {"file": CORE_FILE, "sha256": md380_firmware.sha256(core_data)},
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
