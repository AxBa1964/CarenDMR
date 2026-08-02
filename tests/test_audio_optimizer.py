import unittest
from carendmr.audio import optimize_transmit_pcm

class AudioOptimizerTests(unittest.TestCase):
    def test_optimizer_is_bounded_and_preserves_length(self):
        samples = tuple(12000 if i % 2 else -12000 for i in range(8000))
        result, diagnostics = optimize_transmit_pcm(samples)
        self.assertEqual(len(samples), len(result))
        self.assertTrue(all(-32768 <= value <= 32767 for value in result))
        self.assertGreaterEqual(diagnostics.output_peak_percent, 0.0)

    def test_optimizer_rejects_wrong_sample_rate(self):
        with self.assertRaisesRegex(ValueError, "8 kHz"):
            optimize_transmit_pcm((1, 2, 3), sample_rate=16000)
