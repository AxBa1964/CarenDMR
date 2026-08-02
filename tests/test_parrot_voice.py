import unittest

from carendmr.brandmeister.dmrd import DmrdCallType, DmrdFrameClass, parse_dmrd_packet
from carendmr.brandmeister.parrot_voice import build_locked_parrot_voice_packets


class FakeEncoder:
    def __init__(self): self.calls = 0
    def encode_2450x1150(self, pcm):
        self.calls += 1
        self.last = pcm
        return bytes([self.calls & 0xFF]) * 9
    def close(self): pass


class ParrotVoicePacketTests(unittest.TestCase):
    def test_voice_packets_are_hard_locked_private_9990_ts2(self):
        encoder = FakeEncoder()
        packets = build_locked_parrot_voice_packets(
            source_id=2632198, repeater_id=2632198, stream_id=0x11223344,
            first_sequence=250, pcm_samples=(100,) * 800, encoder=encoder,
        )
        self.assertTrue(packets[0].is_voice_lc_header)
        self.assertTrue(packets[-1].is_terminator_with_lc)
        self.assertEqual(4, len(packets))  # header, 2 voice bursts, terminator
        for packet in packets:
            raw = packet.to_bytes()
            self.assertEqual(9990, packet.destination_id)
            self.assertEqual(2, packet.timeslot)
            self.assertIs(DmrdCallType.PRIVATE, packet.call_type)
            self.assertTrue(raw[15] & 0x40)
            self.assertEqual(packet, parse_dmrd_packet(raw))
        self.assertIs(DmrdFrameClass.VOICE_SYNC, packets[1].frame_class)
        self.assertIs(DmrdFrameClass.VOICE, packets[2].frame_class)

    def test_more_than_hundred_eighty_seconds_is_rejected(self):
        with self.assertRaisesRegex(Exception, "180-Sekunden"):
            build_locked_parrot_voice_packets(
                source_id=1, repeater_id=1, stream_id=1, first_sequence=0,
                pcm_samples=(0,) * 1440001, encoder=FakeEncoder(),
            )

    def test_no_target_or_call_type_parameters_exist(self):
        import inspect
        params = inspect.signature(build_locked_parrot_voice_packets).parameters
        self.assertNotIn("destination_id", params)
        self.assertNotIn("call_type", params)
        self.assertNotIn("timeslot", params)


if __name__ == "__main__": unittest.main()
