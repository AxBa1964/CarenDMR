import unittest

from carendmr.brandmeister.dmrd import (
    DmrdCallType,
    DmrdFrameClass,
    DmrdPacket,
)
from carendmr.brandmeister.silent_call import (
    build_tg91_ts2_silent_call_fixture,
)
from carendmr.vocoder import extract_ambe_codewords


class DmrAmbeExtractionTests(unittest.TestCase):
    @staticmethod
    def _fixture_packets():
        return build_tg91_ts2_silent_call_fixture(
            source_id=1_234_567,
            repeater_id=1_234_567,
            stream_id=0x12345678,
        ).packets

    def test_extracts_three_known_droidstar_silence_codewords(self):
        codewords = extract_ambe_codewords(self._fixture_packets()[1])
        self.assertEqual(
            codewords,
            (bytes.fromhex("b9e881526173002a6b"),) * 3,
        )

    def test_extracts_from_voice_and_voice_sync_only(self):
        voice = self._fixture_packets()[2]
        self.assertEqual(len(extract_ambe_codewords(voice)), 3)

        signaling = DmrdPacket(
            sequence=1,
            source_id=1,
            destination_id=91,
            repeater_id=1,
            timeslot=2,
            call_type=DmrdCallType.GROUP,
            frame_class=DmrdFrameClass.DATA_SYNC,
            stream_id=1,
            payload=bytes(33),
            data_type=1,
        )
        with self.assertRaisesRegex(ValueError, "Sprachrahmen"):
            extract_ambe_codewords(signaling)


if __name__ == "__main__":
    unittest.main()
