import unittest

import numpy as np

from carendmr.application.audio_send_service import _SpeechBandDecimator16kTo8k


class SpeechResamplerTests(unittest.TestCase):
    def test_preserves_exact_half_sample_count_across_blocks(self):
        resampler = _SpeechBandDecimator16kTo8k()
        output = []
        for _ in range(10):
            output.extend(resampler.process(np.zeros(320, dtype=np.float32)))
        self.assertEqual(1600, len(output))

    def test_is_continuous_across_block_boundaries(self):
        signal = np.sin(2 * np.pi * 1000 * np.arange(3200) / 16000).astype(np.float32)
        whole = _SpeechBandDecimator16kTo8k().process(signal)
        split_filter = _SpeechBandDecimator16kTo8k()
        split = np.concatenate([split_filter.process(block) for block in np.split(signal, 10)])
        np.testing.assert_allclose(whole, split, atol=1e-6)

    def test_attenuates_frequencies_above_new_nyquist_limit(self):
        t = np.arange(16000, dtype=np.float32) / 16000.0
        passband = np.sin(2 * np.pi * 1000 * t)
        stopband = np.sin(2 * np.pi * 6000 * t)
        pass_output = _SpeechBandDecimator16kTo8k().process(passband)[100:]
        stop_output = _SpeechBandDecimator16kTo8k().process(stopband)[100:]
        pass_rms = float(np.sqrt(np.mean(pass_output ** 2)))
        stop_rms = float(np.sqrt(np.mean(stop_output ** 2)))
        self.assertLess(stop_rms, pass_rms * 0.03)


if __name__ == "__main__":
    unittest.main()
