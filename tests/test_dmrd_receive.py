import unittest

from carendmr.brandmeister import (
    DMRD_PAYLOAD_SIZE,
    DmrdReceiveActivity,
    build_tg91_terminator_with_lc,
    build_tg91_voice_frame,
    build_tg91_voice_lc_header,
    build_tg91_voice_sync,
    parse_dmrd_receive_event,
)


class DmrdReceiveEventTests(unittest.TestCase):
    SOURCE_ID = 0x010203
    REPEATER_ID = 0x01020304
    STREAM_ID = 0x11223344
    PAYLOAD = bytes(DMRD_PAYLOAD_SIZE)

    def build_bytes(self, builder, **changes):
        arguments = {
            "sequence": 7,
            "source_id": self.SOURCE_ID,
            "repeater_id": self.REPEATER_ID,
            "stream_id": self.STREAM_ID,
            "payload": self.PAYLOAD,
        }
        arguments.update(changes)
        return builder(**arguments).to_bytes()

    def test_header_and_terminator_map_to_call_boundaries(self):
        header = parse_dmrd_receive_event(
            self.build_bytes(build_tg91_voice_lc_header)
        )
        terminator = parse_dmrd_receive_event(
            self.build_bytes(build_tg91_terminator_with_lc)
        )

        self.assertEqual(DmrdReceiveActivity.CALL_START, header.activity)
        self.assertEqual(DmrdReceiveActivity.CALL_END, terminator.activity)

    def test_voice_sync_and_numbered_voice_map_to_voice(self):
        sync = parse_dmrd_receive_event(self.build_bytes(build_tg91_voice_sync))
        voice = parse_dmrd_receive_event(
            self.build_bytes(build_tg91_voice_frame, voice_frame_number=3)
        )

        self.assertEqual(DmrdReceiveActivity.VOICE, sync.activity)
        self.assertEqual(DmrdReceiveActivity.VOICE, voice.activity)
        self.assertIsNone(sync.voice_frame_number)
        self.assertEqual(3, voice.voice_frame_number)

    def test_event_is_payload_free_and_keeps_status_metadata(self):
        event = parse_dmrd_receive_event(self.build_bytes(build_tg91_voice_sync))

        self.assertFalse(hasattr(event, "payload"))
        self.assertEqual(self.SOURCE_ID, event.source_id)
        self.assertEqual(91, event.destination_id)
        self.assertEqual(2, event.timeslot)
        self.assertEqual(self.STREAM_ID, event.stream_id)
        self.assertTrue(event.is_target_group)

    def test_zero_stream_id_becomes_none_without_losing_event(self):
        datagram = bytearray(self.build_bytes(build_tg91_voice_sync))
        datagram[16:20] = b"\x00\x00\x00\x00"

        event = parse_dmrd_receive_event(bytes(datagram))

        self.assertIsNone(event.stream_id)
        self.assertEqual(DmrdReceiveActivity.VOICE, event.activity)
        self.assertTrue(event.is_target_group)

    def test_malformed_datagram_is_still_rejected(self):
        with self.assertRaisesRegex(ValueError, "55"):
            parse_dmrd_receive_event(b"DMRDshort")


if __name__ == "__main__":
    unittest.main()
