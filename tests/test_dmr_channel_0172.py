import unittest
from pathlib import Path

from carendmr.domain import DmrChannel
from _ui_sources import main_window_source


class DmrChannel0172Tests(unittest.TestCase):
    def test_dmr_channel_normalizes_text_fields_and_call_type(self) -> None:
        channel = DmrChannel(262, 2, " GROUP ", " Deutschland ", " Deutschland ", " national ").normalized()
        self.assertEqual(channel.target, 262)
        self.assertEqual(channel.timeslot, 2)
        self.assertEqual(channel.call_type, "group")
        self.assertEqual(channel.name, "Deutschland")
        self.assertEqual(channel.country, "Deutschland")
        self.assertEqual(channel.description, "national")
        self.assertEqual(channel.target_label, "Talkgroup")

    def test_private_channel_uses_dmr_id_label(self) -> None:
        channel = DmrChannel(2632198, 2, "private", "Heidi").normalized()
        self.assertEqual(channel.target_label, "DMR-ID")
        self.assertFalse(channel.is_group_call)

    def test_invalid_dmr_channels_are_rejected(self) -> None:
        for channel in (
            DmrChannel(0, 2, "group"),
            DmrChannel(91, 3, "group"),
            DmrChannel(91, 2, "unknown"),
        ):
            with self.subTest(channel=channel), self.assertRaises(ValueError):
                channel.normalized()

    def test_operation_page_uses_dmr_channel_wording(self) -> None:
        source = main_window_source()
        self.assertIn('QLabel("DMR-KANAL")', source)
        self.assertIn('setPlaceholderText("Talkgroup nach Nummer oder Name suchen")', source)
        self.assertIn('setAccessibleName("Talkgroup")', source)
        self.assertNotIn('QLabel("FUNKZIEL")', source)


if __name__ == "__main__":
    unittest.main()
