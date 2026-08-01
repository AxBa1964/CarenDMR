import unittest

from carendmr.domain import CurrentCall


class CurrentCallTests(unittest.TestCase):
    def test_duration_is_updated_without_mutating_original(self):
        call = CurrentCall(2_632_198, 91, 2, 1234)
        updated = call.with_elapsed(12.5)
        self.assertEqual(0.0, call.elapsed_seconds)
        self.assertEqual(12.5, updated.elapsed_seconds)

    def test_negative_duration_is_clamped(self):
        call = CurrentCall(2_632_198, 91, 2, None)
        self.assertEqual(0.0, call.with_elapsed(-1).elapsed_seconds)


if __name__ == "__main__":
    unittest.main()
