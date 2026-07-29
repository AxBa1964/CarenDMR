import unittest

from carendmr.vocoder.playout import DMR_BURST_SAMPLES, DmrJitterBuffer


def _burst(value):
    return (value,) * DMR_BURST_SAMPLES


class DmrJitterBufferTests(unittest.TestCase):
    def test_prebuffers_and_reorders_three_bursts(self):
        jitter = DmrJitterBuffer(prebuffer_bursts=3)

        self.assertFalse(jitter.push(10, _burst(10)).frames)
        self.assertFalse(jitter.push(12, _burst(12)).frames)
        result = jitter.push(11, _burst(11))

        self.assertEqual([frame[0] for frame in result.frames], [10, 11, 12])
        self.assertEqual(result.concealed_bursts, 0)

    def test_conceals_gap_after_reorder_window(self):
        jitter = DmrJitterBuffer(prebuffer_bursts=1, reorder_bursts=2)
        self.assertEqual(jitter.push(20, _burst(20)).frames[0][0], 20)
        self.assertFalse(jitter.push(22, _burst(22)).frames)
        result = jitter.push(23, _burst(23))

        self.assertEqual([frame[0] for frame in result.frames], [0, 22, 23])
        self.assertEqual(result.concealed_bursts, 1)

    def test_late_duplicate_is_ignored(self):
        jitter = DmrJitterBuffer(prebuffer_bursts=1)
        jitter.push(30, _burst(30))
        self.assertFalse(jitter.push(30, _burst(99)).frames)


if __name__ == "__main__":
    unittest.main()
