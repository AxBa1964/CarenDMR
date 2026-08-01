import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from carendmr import app


class FakeResult:
    authenticated = True
    audio_started = True
    elapsed_seconds = 12.5
    datagrams = 12
    target_voice_bursts = 6
    decoded_codewords = 18
    decoded_samples = 2880
    decode_errors = 0
    corrected_errors = 0
    concealed_bursts = 0
    invalid_dmrd = 0
    interrupted = True
    closed = True


class AppEntrypointTests(unittest.TestCase):
    def test_parser_offers_unlimited_listen_by_default(self):
        parser = app._build_parser()
        args = parser.parse_args(["--listen"])
        self.assertTrue(args.listen)
        self.assertIsNone(args.duration)

    def test_parser_accepts_explicit_duration(self):
        parser = app._build_parser()
        args = parser.parse_args(["--listen", "--duration", "600"])
        self.assertEqual(600.0, args.duration)

    def test_live_listen_uses_requested_duration_and_progress(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "config").mkdir()
            (root / "config" / "brandmeister.local.json").write_text("{}", encoding="utf-8")

            with patch.object(app.BrandMeisterConfigStore, "load", return_value=object()), patch.object(
                app, "listen_receive_only", return_value=FakeResult()
            ) as listen:
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    result = app._run_live_listen(root, seconds=600.0)

            self.assertEqual(0, result)
            listen.assert_called_once_with(
                unittest.mock.ANY,
                seconds=600.0,
                progress_callback=app._print_progress,
                call_activity_callback=app._print_call_activity,
            )
            self.assertIn("DMRD gesendet:              0", output.getvalue())
            self.assertIn("Beendigung:                Strg+C", output.getvalue())

    def test_duration_without_listen_is_rejected(self):
        error = io.StringIO()
        with contextlib.redirect_stderr(error):
            result = app.run(["--duration", "600"])
        self.assertEqual(2, result)
        self.assertIn("nur zusammen mit --listen", error.getvalue())

    def test_excessive_duration_is_rejected(self):
        error = io.StringIO()
        with contextlib.redirect_stderr(error):
            result = app.run(["--listen", "--duration", "3601"])
        self.assertEqual(2, result)

    def test_live_listen_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "config").mkdir()

            with patch.object(
                app.BrandMeisterConfigStore,
                "load",
                side_effect=RuntimeError("Konfiguration fehlt"),
            ):
                error = io.StringIO()
                with contextlib.redirect_stderr(error):
                    result = app._run_live_listen(root, seconds=None)

            self.assertEqual(2, result)
            self.assertIn("Es wurde kein DMRD-Paket gesendet.", error.getvalue())


if __name__ == "__main__":
    unittest.main()
