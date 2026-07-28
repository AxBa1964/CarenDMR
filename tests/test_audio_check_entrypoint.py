import os
import subprocess
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class AudioCheckEntrypointTests(unittest.TestCase):
    def test_direct_script_start_can_import_project_package(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = ""

        result = subprocess.run(
            [
                sys.executable,
                str(PROJECT_ROOT / "tools" / "audio_check.py"),
                "--help",
            ],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )

        self.assertEqual(
            0,
            result.returncode,
            msg=result.stdout + result.stderr,
        )
        self.assertIn("Audiogeräte erkennen", result.stdout)


if __name__ == "__main__":
    unittest.main()
