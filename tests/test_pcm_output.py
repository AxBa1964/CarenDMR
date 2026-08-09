import unittest

from carendmr.audio.pcm_output import BufferedPcmOutput


class BufferedPcmOutputTests(unittest.TestCase):
    def test_callback_plays_buffer_then_zero_fills_underrun(self):
        output = BufferedPcmOutput(maximum_buffer_seconds=1)
        output.write((1, -1))
        target = bytearray(8)

        output._callback(memoryview(target), 4, None, None)

        self.assertEqual(target, b"\x01\x00\xff\xff\x00\x00\x00\x00")
        self.assertEqual(output.samples_written, 2)
        self.assertEqual(output.samples_played, 4)
        self.assertEqual(output.underrun_callbacks, 1)

    def test_buffer_is_bounded_and_drops_oldest_complete_samples(self):
        output = BufferedPcmOutput(
            sample_rate=4,
            maximum_buffer_seconds=1,
        )
        output.write((1, 2, 3, 4))
        output.write((5, 6))
        target = bytearray(8)
        output._callback(memoryview(target), 4, None, None)

        self.assertEqual(
            target,
            b"\x03\x00\x04\x00\x05\x00\x06\x00",
        )
        self.assertEqual(output.dropped_samples, 2)

    def test_muted_callback_discards_buffer_and_outputs_silence(self):
        muted = True
        output = BufferedPcmOutput(sample_rate=8000, maximum_buffer_seconds=1, muted=lambda: muted)
        output.write([100, 200, 300])
        target = bytearray(6)
        output._callback(memoryview(target), 3, None, None)
        self.assertEqual(bytes(6), bytes(target))
        self.assertEqual(0, len(output._buffer))

    def test_callback_applies_output_volume(self):
        output = BufferedPcmOutput(sample_rate=8000, maximum_buffer_seconds=1.0, volume=lambda: 0.5)
        output.write([1000, -1000])
        data = bytearray(4)
        output._callback(memoryview(data), 2, None, None)
        import struct
        self.assertEqual((500, -500), struct.unpack("<2h", data))

    def test_callback_at_100_percent_preserves_valid_pcm16_samples(self):
        import struct
        output = BufferedPcmOutput(sample_rate=8000, maximum_buffer_seconds=1.0, volume=lambda: 1.0)
        source = (1000, -1000, 12000, -12000, 30000, -30000, 32767, -32768)
        output.write(source)
        data = bytearray(len(source) * 2)
        output._callback(memoryview(data), len(source), None, None)
        self.assertEqual(source, struct.unpack("<8h", data))

    def test_callback_supports_amplification_with_pcm16_clipping(self):
        import struct
        levels = []
        output = BufferedPcmOutput(
            sample_rate=8000, maximum_buffer_seconds=1.0,
            volume=lambda: 4.0, level_callback=levels.append,
        )
        output.write([12000, -12000])
        data = bytearray(4)
        output._callback(memoryview(data), 2, None, None)
        values = struct.unpack("<2h", data)
        self.assertGreater(values[0], 12000)
        self.assertLess(values[1], -12000)
        self.assertTrue(all(-32768 <= value <= 32767 for value in values))
        self.assertGreater(levels[-1], 0.0)

    def test_agc_raises_quiet_speech_gradually(self):
        import struct
        output = BufferedPcmOutput(
            sample_rate=8000, maximum_buffer_seconds=1.0,
            volume=lambda: 1.0, agc_enabled=lambda: True,
        )
        result = None
        for _ in range(40):
            output.write([1000] * 160)
            data = bytearray(320)
            output._callback(memoryview(data), 160, None, None)
            result = struct.unpack("<160h", data)
        self.assertIsNotNone(result)
        self.assertGreater(result[0], 1000)


if __name__ == "__main__":
    unittest.main()
