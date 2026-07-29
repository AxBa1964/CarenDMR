import subprocess
import unittest

from carendmr.accessibility import MacOSSpeechOutput


class MacOSSpeechOutputTests(unittest.TestCase):
    def test_uses_local_say_without_shell(self):
        calls = []

        def runner(*args, **kwargs):
            calls.append((args, kwargs))
            return subprocess.CompletedProcess(args[0], 0)

        MacOSSpeechOutput(runner).speak("Sicherer Test.")

        self.assertEqual(["say", "Sicherer Test."], calls[0][0][0])
        self.assertNotIn("shell", calls[0][1])
        self.assertTrue(calls[0][1]["check"])

    def test_failure_has_non_sensitive_message(self):
        def runner(*_args, **_kwargs):
            raise OSError("private system detail")

        with self.assertRaisesRegex(RuntimeError, "nicht verfügbar"):
            MacOSSpeechOutput(runner).speak("Test")


if __name__ == "__main__":
    unittest.main()
