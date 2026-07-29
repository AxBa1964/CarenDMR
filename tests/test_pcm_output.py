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


if __name__ == "__main__":
    unittest.main()
