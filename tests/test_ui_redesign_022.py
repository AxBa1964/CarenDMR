from pathlib import Path
import tempfile
import unittest

from carendmr.diagnostics.runtime import initialize, is_enabled, set_enabled


class UiRedesign022Tests(unittest.TestCase):
    # Die Quelltext-Tests der entfernten Tkinter-Oberfläche entfielen mit 0.2.1.87.

    def test_diagnostics_can_be_switched_off_and_persisted(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertFalse(initialize(root))
            set_enabled(True)
            self.assertTrue(is_enabled())
            self.assertTrue(initialize(root))
            set_enabled(False)
            self.assertFalse(is_enabled())


if __name__ == "__main__":
    unittest.main()
