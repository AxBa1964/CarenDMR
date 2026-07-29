import unittest
from dataclasses import FrozenInstanceError

from carendmr.brandmeister import (
    DMRD_PACKET_SIZE,
    DMRD_PAYLOAD_SIZE,
    TARGET_TALKGROUP,
    TARGET_TIMESLOT,
    DmrdCallType,
    DmrdDataType,
    DmrdFrameClass,
    DmrdPacket,
    build_tg91_terminator_with_lc,
    build_tg91_voice_frame,
    build_tg91_voice_lc_header,
    build_tg91_voice_sync,
    parse_dmrd_packet,
)


class DmrdPacketTests(unittest.TestCase):
    SOURCE_ID = 0x010203
    REPEATER_ID = 0x01020304
    STREAM_ID = 0x11223344
    PAYLOAD = bytes(range(DMRD_PAYLOAD_SIZE))

    def test_tg91_voice_lc_header_has_homebrew_layout(self):
        model = build_tg91_voice_lc_header(
            sequence=7,
            source_id=self.SOURCE_ID,
            repeater_id=self.REPEATER_ID,
            stream_id=self.STREAM_ID,
            payload=self.PAYLOAD,
        )

        packet = model.to_bytes()

        self.assertEqual(DMRD_PACKET_SIZE, len(packet))
        self.assertEqual(b"DMRD", packet[:4])
        self.assertEqual(7, packet[4])
        self.assertEqual(self.SOURCE_ID.to_bytes(3, "big"), packet[5:8])
        self.assertEqual(TARGET_TALKGROUP.to_bytes(3, "big"), packet[8:11])
        self.assertEqual(self.REPEATER_ID.to_bytes(4, "big"), packet[11:15])
        self.assertEqual(0xA1, packet[15])
        self.assertEqual(self.STREAM_ID.to_bytes(4, "big"), packet[16:20])
        self.assertEqual(self.PAYLOAD, packet[20:53])
        self.assertEqual(b"\x00\x00", packet[53:55])

    def test_voice_sync_voice_frames_and_terminator_flags(self):
        sync = build_tg91_voice_sync(
            sequence=8,
            source_id=self.SOURCE_ID,
            repeater_id=self.REPEATER_ID,
            stream_id=self.STREAM_ID,
            payload=self.PAYLOAD,
        )
        voice = build_tg91_voice_frame(
            sequence=9,
            source_id=self.SOURCE_ID,
            repeater_id=self.REPEATER_ID,
            stream_id=self.STREAM_ID,
            voice_frame_number=3,
            payload=self.PAYLOAD,
        )
        terminator = build_tg91_terminator_with_lc(
            sequence=10,
            source_id=self.SOURCE_ID,
            repeater_id=self.REPEATER_ID,
            stream_id=self.STREAM_ID,
            payload=self.PAYLOAD,
        )

        self.assertEqual(0x90, sync.to_bytes()[15])
        self.assertEqual(0x83, voice.to_bytes()[15])
        self.assertEqual(0xA2, terminator.to_bytes()[15])
        self.assertTrue(sync.is_target_group)
        self.assertTrue(voice.is_target_group)
        self.assertTrue(terminator.is_target_group)

    def test_parser_models_header_and_preserves_packet(self):
        original = DmrdPacket(
            sequence=255,
            source_id=self.SOURCE_ID,
            destination_id=TARGET_TALKGROUP,
            repeater_id=self.REPEATER_ID,
            timeslot=TARGET_TIMESLOT,
            call_type=DmrdCallType.GROUP,
            frame_class=DmrdFrameClass.DATA_SYNC,
            stream_id=self.STREAM_ID,
            payload=self.PAYLOAD,
            ber=4,
            rssi=99,
            data_type=DmrdDataType.VOICE_LC_HEADER.value,
        )

        parsed = parse_dmrd_packet(original.to_bytes())

        self.assertEqual(original, parsed)
        self.assertTrue(parsed.is_target_group)
        self.assertTrue(parsed.is_voice_lc_header)
        self.assertFalse(parsed.is_terminator_with_lc)

    def test_parser_models_private_timeslot_one_voice_frame(self):
        flags = 0x40 | 0x05
        packet = b"".join(
            (
                b"DMRD",
                b"\x01",
                self.SOURCE_ID.to_bytes(3, "big"),
                b"\x00\x00\x09",
                self.REPEATER_ID.to_bytes(4, "big"),
                bytes((flags,)),
                self.STREAM_ID.to_bytes(4, "big"),
                self.PAYLOAD,
                b"\x02\x03",
            )
        )

        parsed = parse_dmrd_packet(packet)

        self.assertEqual(1, parsed.timeslot)
        self.assertEqual(DmrdCallType.PRIVATE, parsed.call_type)
        self.assertEqual(DmrdFrameClass.VOICE, parsed.frame_class)
        self.assertEqual(5, parsed.voice_frame_number)
        self.assertFalse(parsed.is_target_group)

    def test_parser_rejects_wrong_tag_length_and_reserved_flags(self):
        valid = build_tg91_voice_sync(
            sequence=1,
            source_id=self.SOURCE_ID,
            repeater_id=self.REPEATER_ID,
            stream_id=self.STREAM_ID,
            payload=self.PAYLOAD,
        ).to_bytes()

        with self.assertRaisesRegex(ValueError, "55"):
            parse_dmrd_packet(valid[:-1])
        with self.assertRaisesRegex(ValueError, "Kennung"):
            parse_dmrd_packet(b"NOPE" + valid[4:])

        reserved = bytearray(valid)
        reserved[15] = 0xB0
        with self.assertRaisesRegex(ValueError, "reserviert"):
            parse_dmrd_packet(bytes(reserved))

    def test_voice_frame_requires_number_zero_through_five(self):
        for frame_number in (-1, 6):
            with self.subTest(frame_number=frame_number):
                with self.assertRaisesRegex(ValueError, "zwischen 0 und 5"):
                    build_tg91_voice_frame(
                        sequence=1,
                        source_id=self.SOURCE_ID,
                        repeater_id=self.REPEATER_ID,
                        stream_id=self.STREAM_ID,
                        voice_frame_number=frame_number,
                        payload=self.PAYLOAD,
                    )

    def test_payload_and_identifiers_are_strictly_validated(self):
        with self.assertRaisesRegex(ValueError, "33"):
            build_tg91_voice_sync(
                sequence=1,
                source_id=self.SOURCE_ID,
                repeater_id=self.REPEATER_ID,
                stream_id=self.STREAM_ID,
                payload=b"short",
            )
        with self.assertRaisesRegex(ValueError, "Quell-ID"):
            build_tg91_voice_sync(
                sequence=1,
                source_id=0,
                repeater_id=self.REPEATER_ID,
                stream_id=self.STREAM_ID,
                payload=self.PAYLOAD,
            )

    def test_packet_model_is_immutable(self):
        packet = build_tg91_voice_sync(
            sequence=1,
            source_id=self.SOURCE_ID,
            repeater_id=self.REPEATER_ID,
            stream_id=self.STREAM_ID,
            payload=self.PAYLOAD,
        )

        with self.assertRaises(FrozenInstanceError):
            packet.sequence = 2


if __name__ == "__main__":
    unittest.main()
