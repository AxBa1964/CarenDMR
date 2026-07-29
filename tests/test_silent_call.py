import unittest
from dataclasses import FrozenInstanceError

from carendmr.brandmeister import (
    SILENT_CALL_PACKET_COUNT,
    SILENT_VOICE_BURST_COUNT,
    TARGET_TALKGROUP,
    TARGET_TIMESLOT,
    DmrdFrameClass,
    build_tg91_ts2_silent_call_fixture,
    parse_dmrd_packet,
)


class SilentCallFixtureTests(unittest.TestCase):
    SOURCE_ID = 0x010203
    REPEATER_ID = 0x01020304
    STREAM_ID = 0x11223344

    # Generated independently by a temporary C++ oracle compiled from
    # DroidStar commit 5368b41d1b832d356a066fafa9992187a72316e1.
    REFERENCE_PAYLOADS = tuple(
        bytes.fromhex(value)
        for value in (
            "00150a4410a019507f007980046d5d7f77fd757e3304000801a0038003010c0379",
            "b9e881526173002a6bb9e8815267f7d5dd57dfd173002a6bb9e881526173002a6b",
            "b9e881526173002a6bb9e881526130309090591173002a6bb9e881526173002a6b",
            "b9e881526173002a6bb9e881526170909000074173002a6bb9e881526173002a6b",
            "b9e881526173002a6bb9e881526170312090c74173002a6bb9e881526173002a6b",
            "b9e881526173002a6bb9e881526151d17031b07173002a6bb9e881526173002a6b",
            "b9e881526173002a6bb9e8815261100000000e2173002a6bb9e881526173002a6b",
            "007a0a90101019287f70792004ad5d7f77fd75796610033006c00fc00b0115034a",
        )
    )

    def build_fixture(self, first_sequence=250):
        return build_tg91_ts2_silent_call_fixture(
            source_id=self.SOURCE_ID,
            repeater_id=self.REPEATER_ID,
            stream_id=self.STREAM_ID,
            first_sequence=first_sequence,
        )

    def test_payloads_match_droidstar_reference_byte_for_byte(self):
        fixture = self.build_fixture()

        self.assertEqual(
            self.REFERENCE_PAYLOADS,
            tuple(packet.payload for packet in fixture.packets),
        )

    def test_fixture_has_header_six_voice_bursts_and_terminator(self):
        fixture = self.build_fixture()
        packets = fixture.packets

        self.assertEqual(SILENT_CALL_PACKET_COUNT, len(packets))
        self.assertEqual(SILENT_VOICE_BURST_COUNT, len(packets[1:7]))
        self.assertTrue(packets[0].is_voice_lc_header)
        self.assertEqual(DmrdFrameClass.VOICE_SYNC, packets[1].frame_class)
        self.assertEqual(
            [1, 2, 3, 4, 5],
            [packet.voice_frame_number for packet in packets[2:7]],
        )
        self.assertTrue(packets[7].is_terminator_with_lc)

    def test_every_packet_is_target_group_and_round_trips(self):
        fixture = self.build_fixture()

        for packet in fixture.packets:
            with self.subTest(sequence=packet.sequence):
                self.assertEqual(TARGET_TALKGROUP, packet.destination_id)
                self.assertEqual(TARGET_TIMESLOT, packet.timeslot)
                self.assertTrue(packet.is_target_group)
                self.assertEqual(packet, parse_dmrd_packet(packet.to_bytes()))

    def test_sequences_wrap_without_changing_stream(self):
        fixture = self.build_fixture(first_sequence=250)

        self.assertEqual(
            [250, 251, 252, 253, 254, 255, 0, 1],
            [packet.sequence for packet in fixture.packets],
        )
        self.assertEqual(
            {self.STREAM_ID},
            {packet.stream_id for packet in fixture.packets},
        )

    def test_fixture_and_packets_are_immutable(self):
        fixture = self.build_fixture()

        with self.assertRaises(FrozenInstanceError):
            fixture.packets = ()
        with self.assertRaises(FrozenInstanceError):
            fixture.packets[0].sequence = 4

    def test_public_inputs_are_strictly_validated(self):
        invalid_cases = (
            ({"source_id": 0}, "Quell-ID"),
            ({"repeater_id": 0}, "Repeater-ID"),
            ({"stream_id": 0}, "Stream-ID"),
            ({"first_sequence": -1}, "Sequenznummer"),
            ({"first_sequence": 256}, "Sequenznummer"),
        )
        defaults = {
            "source_id": self.SOURCE_ID,
            "repeater_id": self.REPEATER_ID,
            "stream_id": self.STREAM_ID,
            "first_sequence": 0,
        }

        for override, message in invalid_cases:
            with self.subTest(override=override):
                arguments = defaults | override
                with self.assertRaisesRegex(ValueError, message):
                    build_tg91_ts2_silent_call_fixture(**arguments)

    def test_fixture_has_no_network_side_effect(self):
        fixture = self.build_fixture()

        self.assertFalse(hasattr(fixture, "send"))
        self.assertFalse(hasattr(fixture, "transmit"))
        self.assertEqual(8, len(fixture.to_bytes()))
        self.assertTrue(all(len(packet) == 55 for packet in fixture.to_bytes()))


if __name__ == "__main__":
    unittest.main()
