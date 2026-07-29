from __future__ import annotations

import fnmatch
import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = PROJECT_ROOT / "carendmr" / "version.py"
RELEASE_DIR = PROJECT_ROOT / "release"

EXCLUDED_DIRECTORIES = {
    ".git",
    ".idea",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "logs",
    "release",
    "venv",
}

EXCLUDED_PATTERNS = {
    "*.pyc",
    "*.pyo",
    "*.spec",
    "*.zip",
    "*.local.json",
    "Desktop.ini",
    "Thumbs.db",
}

REQUIRED_FILES = {
    ".gitignore",
    "CHANGELOG.md",
    "DEPLOY.md",
    "LICENSE",
    "README.md",
    "RELEASE_INFO.md",
    "main.py",
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


def should_exclude(relative_path: Path) -> bool:
    if any(part in EXCLUDED_DIRECTORIES for part in relative_path.parts):
        return True

    return any(
        fnmatch.fnmatch(relative_path.name, pattern)
        for pattern in EXCLUDED_PATTERNS
    )


def collect_release_files(project_root: Path = PROJECT_ROOT) -> list[Path]:
    files: list[Path] = []

    for path in sorted(project_root.rglob("*")):
        if not path.is_file():
            continue

        relative_path = path.relative_to(project_root)
        if should_exclude(relative_path):
            continue

        files.append(path)

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
