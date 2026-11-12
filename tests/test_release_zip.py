import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.create_release_zip import (
    ReleaseError,
    collect_release_files,
    create_release,
    read_version,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _init_git_repo(root: Path, gitignore: str) -> None:
    """Legt ein leeres Git-Repo an; die Dateiauswahl erfolgt über git ls-files."""
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    (root / ".gitignore").write_text(gitignore, encoding="utf-8")


def _write(root: Path, relative_path: str, content: str = "x\n") -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@unittest.skipUnless(shutil.which("git"), "Git wird für die Release-Dateiauswahl benötigt.")
class ReleaseZipTests(unittest.TestCase):
    def test_read_version(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            version_file = Path(temp_dir) / "version.py"
            version_file.write_text('__version__ = "1.2.3"\n', encoding="utf-8")

            self.assertEqual("1.2.3", read_version(version_file))

    def test_missing_version_raises_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            version_file = Path(temp_dir) / "version.py"
            version_file.write_text("name = 'CarenDMR'\n", encoding="utf-8")

            with self.assertRaises(ReleaseError):
                read_version(version_file)

    def test_project_gitignore_excludes_local_and_generated_files(self):
        """Die echte .gitignore des Projekts bestimmt, was ins Release-ZIP darf."""
        gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
        excluded = [
            "release/CarenDMR_0.0.2.zip",
            "logs/carendmr.log",
            "carendmr/__pycache__/app.pyc",
            "config/config.local.json",
            "config/brandmeister.local.json",
            "config/audio.local.json",
            "native/libcarendmr_mbe.dylib",
            "native/libcarendmr_mbe.so",
            "native/carendmr_mbe.dll",
            "data/contacts.db",
            "data/radioid_user.csv.part",
            "plugins/vocoder_plugin.winnt.x86_64",
            "tests/test_example.py.tmp",
        ]
        included = ["native/build_windows.ps1", "carendmr/app.py"]

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "project"
            _init_git_repo(root, gitignore)
            for relative_path in excluded + included:
                _write(root, relative_path)

            relative_files = {
                path.relative_to(root).as_posix()
                for path in collect_release_files(root)
            }

        for relative_path in excluded:
            self.assertNotIn(relative_path, relative_files)
        for relative_path in included:
            self.assertIn(relative_path, relative_files)

    def test_collect_release_files_skips_zip_and_logs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "project"
            _init_git_repo(root, "*.zip\nlogs/\n")
            _write(root, "main.py", "print('ok')\n")
            _write(root, "carendmr/app.py", "pass\n")
            (root / "old.zip").write_bytes(b"zip")
            _write(root, "logs/test.log", "log\n")

            relative_files = {
                path.relative_to(root).as_posix()
                for path in collect_release_files(root)
            }

            self.assertEqual({".gitignore", "main.py", "carendmr/app.py"}, relative_files)

    def test_create_release_contains_required_source_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "project"
            release_dir = Path(temp_dir) / "output"

            required_files = {
                "CHANGELOG.md": "# Changelog\n",
                "DEPLOY.md": "# Deploy\n",
                "LICENSE": "GPL-3.0-or-later\n",
                "README.md": "# README\n",
                "RELEASE_INFO.md": "# Release\n",
                "main.py": "print('ok')\n",
                "native/build_windows.ps1": "Write-Host 'build'\n",
                "native/build_vocoder_bridge_windows.ps1": "Write-Host 'bridge'\n",
                "native/build_vocoder_bridge.sh": "#!/bin/sh\n",
                "native/vocoder_plugin_bridge.cpp": "// bridge\n",
                "requirements.txt": "\n",
                "carendmr/version.py": '__version__ = "9.9.9"\n',
                "config/config.json": "{}\n",
                "docs/UPSTREAM_PROVENANCE.md": "# Provenienz\n",
            }

            _init_git_repo(root, "*.zip\nlogs/\n")
            for relative_path, content in required_files.items():
                _write(root, relative_path, content)
            _write(root, "logs/carendmr.log", "log\n")
            (root / "old.zip").write_bytes(b"old")

            archive_path, file_count = create_release(root, release_dir)

            self.assertEqual("CarenDMR_Projekt_9.9.9.zip", archive_path.name)
            # Pflichtdateien plus die .gitignore selbst.
            self.assertEqual(len(required_files) + 1, file_count)

            with zipfile.ZipFile(archive_path) as archive:
                names = set(archive.namelist())

            self.assertIn(".gitignore", names)
            self.assertIn("main.py", names)
            self.assertIn("native/build_windows.ps1", names)
            self.assertIn("native/build_vocoder_bridge_windows.ps1", names)
            self.assertIn("native/vocoder_plugin_bridge.cpp", names)
            self.assertIn("LICENSE", names)
            self.assertIn("carendmr/version.py", names)
            self.assertIn("docs/UPSTREAM_PROVENANCE.md", names)
            self.assertNotIn("logs/carendmr.log", names)
            self.assertNotIn("old.zip", names)

    def test_missing_required_file_raises_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "project"
            _init_git_repo(root, "")
            _write(root, "main.py")

            with self.assertRaises(ReleaseError):
                create_release(root, Path(temp_dir) / "output")


if __name__ == "__main__":
    unittest.main()
