import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.create_release_zip import (
    ReleaseError,
    collect_release_files,
    create_release,
    read_version,
    should_exclude,
)


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

    def test_excluded_paths(self):
        self.assertTrue(should_exclude(Path("release/CarenDMR_0.0.2.zip")))
        self.assertTrue(should_exclude(Path("logs/carendmr.log")))
        self.assertTrue(should_exclude(Path("carendmr/__pycache__/app.pyc")))
        self.assertTrue(should_exclude(Path("config/config.local.json")))
        self.assertTrue(should_exclude(Path("config/brandmeister.local.json")))
        self.assertTrue(should_exclude(Path("config/audio.local.json")))
        self.assertTrue(should_exclude(Path("native/libcarendmr_mbe.dylib")))
        self.assertTrue(should_exclude(Path("native/libcarendmr_mbe.so")))
        self.assertFalse(should_exclude(Path("carendmr/app.py")))

    def test_collect_release_files_skips_zip_and_logs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "carendmr").mkdir()
            (root / "logs").mkdir()
            (root / "main.py").write_text("print('ok')\n", encoding="utf-8")
            (root / "old.zip").write_bytes(b"zip")
            (root / "logs" / "test.log").write_text("log\n", encoding="utf-8")
            (root / "carendmr" / "app.py").write_text("pass\n", encoding="utf-8")

            relative_files = {
                path.relative_to(root).as_posix()
                for path in collect_release_files(root)
            }

            self.assertEqual({"main.py", "carendmr/app.py"}, relative_files)

    def test_create_release_contains_required_source_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "project"
            release_dir = Path(temp_dir) / "output"

            required_files = {
                ".gitignore": "*.zip\n",
                "CHANGELOG.md": "# Changelog\n",
                "DEPLOY.md": "# Deploy\n",
                "LICENSE": "GPL-3.0-or-later\n",
                "README.md": "# README\n",
                "RELEASE_INFO.md": "# Release\n",
                "main.py": "print('ok')\n",
                "requirements.txt": "\n",
                "carendmr/version.py": '__version__ = "9.9.9"\n',
                "config/config.json": "{}\n",
                "docs/UPSTREAM_PROVENANCE.md": "# Provenienz\n",
            }

            for relative_path, content in required_files.items():
                path = root / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")

            (root / "logs").mkdir()
            (root / "logs" / "carendmr.log").write_text("log\n", encoding="utf-8")
            (root / "old.zip").write_bytes(b"old")

            archive_path, file_count = create_release(root, release_dir)

            self.assertEqual("CarenDMR_9.9.9.zip", archive_path.name)
            self.assertEqual(len(required_files), file_count)

            with zipfile.ZipFile(archive_path) as archive:
                names = set(archive.namelist())

            self.assertIn("main.py", names)
            self.assertIn("LICENSE", names)
            self.assertIn("carendmr/version.py", names)
            self.assertIn("docs/UPSTREAM_PROVENANCE.md", names)
            self.assertNotIn("logs/carendmr.log", names)
            self.assertNotIn("old.zip", names)


if __name__ == "__main__":
    unittest.main()
