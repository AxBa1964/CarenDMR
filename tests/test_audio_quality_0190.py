import tempfile
import unittest
from pathlib import Path

import numpy as np

from carendmr.audio import StreamingTxSpeechProcessor
from carendmr.application import AudioSendService


class AudioQuality190Tests(unittest.TestCase):
    def test_streaming_processor_removes_dc_and_preserves_length(self):
        processor = StreamingTxSpeechProcessor(sample_rate=16000, enabled=True)
        source = np.full(1600, 0.25, dtype=np.float32)
        result = processor.process(source)
        self.assertEqual(len(source), len(result))
        self.assertLess(abs(float(np.mean(result[-400:]))), 0.01)

    def test_streaming_processor_limits_only_high_peaks(self):
        processor = StreamingTxSpeechProcessor(sample_rate=16000, enabled=True)
        normal = np.sin(2.0 * np.pi * 1000.0 * np.arange(1600) / 16000.0).astype(np.float32) * 0.25
        normal_out = processor.process(normal)
        self.assertLess(float(np.max(np.abs(normal[200:]-normal_out[200:]))), 0.08)
        peaks = np.array([0.0, 1.0, -1.0, 0.0], dtype=np.float32)
        peak_out = processor.process(peaks)
        self.assertLessEqual(float(np.max(np.abs(peak_out))), 0.98)
        self.assertGreater(processor.limited_samples, 0)

    def test_setting_is_enabled_by_default_and_persisted(self):
        class Backend:
            def query_devices(self): return []
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            service = AudioSendService(root, backend=Backend())
            self.assertTrue(service.tx_speech_processing_enabled)
            service.set_tx_speech_processing_enabled(False)
            service.save_settings()
            reloaded = AudioSendService(root, backend=Backend())
            self.assertFalse(reloaded.tx_speech_processing_enabled)


if __name__ == "__main__":
    unittest.main()
