import contextlib
import io
import unittest
from unittest.mock import patch

from carendmr import app


class GuiEntrypointTests(unittest.TestCase):
    def test_gui_argument_starts_ui_lazily(self):
        with patch("carendmr.ui_qt.run_gui", return_value=0) as run_gui:
            self.assertEqual(0, app.run(["--gui"]))
        run_gui.assert_called_once()

    def test_gui_and_console_listen_are_mutually_exclusive(self):
        error = io.StringIO()
        with contextlib.redirect_stderr(error):
            self.assertEqual(2, app.run(["--gui", "--listen"]))
        self.assertIn("nicht gleichzeitig", error.getvalue())


if __name__ == "__main__":
    unittest.main()
