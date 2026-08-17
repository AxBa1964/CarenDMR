from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = PROJECT_ROOT / "carendmr" / "version.py"
RELEASE_DIR = PROJECT_ROOT / "release"

REQUIRED_FILES = {
    ".gitignore",
    "CHANGELOG.md",
    "DEPLOY.md",
    "LICENSE",
    "README.md",
    "RELEASE_INFO.md",
    "main.py",
    "native/build_windows.ps1",
    "native/build_vocoder_bridge_windows.ps1",
    "native/build_vocoder_bridge.sh",
    "native/vocoder_plugin_bridge.cpp",
    "requirements.txt",
    "carendmr/version.py",
    "config/config.json",
    "docs/UPSTREAM_PROVENANCE.md",
}


class ReleaseError(RuntimeError):
    """Fehler bei der Release-Erstellung."""


def read_version(version_file: Path = VERSION_FILE) -> str:
    namespace: dict[str, object] = {}

    try:
        source = version_file.read_text(encoding="utf-8")
    except OSError as exc:
        raise ReleaseError(f"Versionsdatei kann nicht gelesen werden: {version_file}") from exc

    try:
        exec(compile(source, str(version_file), "exec"), {}, namespace)
    except Exception as exc:
        raise ReleaseError(f"Versionsdatei ist ungültig: {version_file}") from exc

    version = namespace.get("__version__")
    if not isinstance(version, str) or not version.strip():
        raise ReleaseError("In carendmr/version.py fehlt eine gültige __version__.")

    return version.strip()


def collect_release_files(project_root: Path = PROJECT_ROOT) -> list[Path]:
    try:
        result = subprocess.run(
            [
                "git",
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
                "-z",
            ],
            cwd=project_root,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ReleaseError(
            "Git-Dateiliste konnte nicht ermittelt werden. "
            "Das Release-ZIP wird bewusst nur aus Git/.gitignore erzeugt."
        ) from exc

    relative_paths = [
        Path(raw.decode("utf-8"))
        for raw in result.stdout.split(b"\0")
        if raw
    ]

    files: list[Path] = []
    for relative_path in sorted(relative_paths):
        source_path = project_root / relative_path
        if source_path.is_file():
            files.append(source_path)

    return files


def validate_required_files(project_root: Path = PROJECT_ROOT) -> None:
    missing = sorted(
        relative_path
        for relative_path in REQUIRED_FILES
        if not (project_root / relative_path).is_file()
    )

    if missing:
        formatted = ", ".join(missing)
        raise ReleaseError(f"Pflichtdateien fehlen: {formatted}")


def create_release(
    project_root: Path = PROJECT_ROOT,
    release_dir: Path | None = None,
) -> tuple[Path, int]:
    validate_required_files(project_root)
    version = read_version(project_root / "carendmr" / "version.py")
    files = collect_release_files(project_root)

    target_dir = release_dir or (project_root / "release")
    target_dir.mkdir(parents=True, exist_ok=True)

    archive_path = target_dir / f"CarenDMR_{version}.zip"

    if archive_path.exists():
        archive_path.unlink()

    with zipfile.ZipFile(
        archive_path,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        for source_path in files:
            relative_path = source_path.relative_to(project_root)
            archive.write(source_path, relative_path.as_posix())

    return archive_path, len(files)


def main() -> int:
    try:
        version = read_version()
        archive_path, file_count = create_release()
    except ReleaseError as exc:
        print(f"Release konnte nicht erstellt werden: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Dateisystemfehler: {exc}", file=sys.stderr)
        return 1

    size_kib = archive_path.stat().st_size / 1024

    print("Release erstellt")
    print("-" * 40)
    print(f"Version : {version}")
    print(f"Datei   : {archive_path}")
    print(f"Dateien : {file_count}")
    print(f"Größe   : {size_kib:.1f} KiB")
    print()
    print("Fertig.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
