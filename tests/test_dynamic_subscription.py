import unittest

from carendmr.brandmeister.dmrd import DmrdDataType, parse_dmrd_packet
from carendmr.brandmeister.dynamic_subscription import (
    activate_dynamic_talkgroup,
    build_dynamic_tg_packets,
    validate_receive_target,
)


class FakeTransport:
    def __init__(self):
        self.sent = []

    def send(self, packet):
        self.sent.append(packet)
        return len(packet)


class DynamicSubscriptionTests(unittest.TestCase):
    def test_builds_complete_group_call_pulse_for_selected_target(self):
        packets = build_dynamic_tg_packets(
            dmr_id=2632198, talkgroup=262, timeslot=1, stream_id=1234
        )
        self.assertEqual(8, len(packets))
        self.assertTrue(all(len(packet) == 55 for packet in packets))
        first = parse_dmrd_packet(packets[0])
        last = parse_dmrd_packet(packets[-1])
        self.assertTrue(first.matches_group_target(262, 1))
        self.assertEqual(2632198, first.source_id)
        self.assertEqual(1234, first.stream_id)
        self.assertEqual(DmrdDataType.VOICE_LC_HEADER.value, first.data_type)
        self.assertEqual(DmrdDataType.TERMINATOR_WITH_LC.value, last.data_type)

    def test_activation_uses_existing_transport_without_api(self):
        transport = FakeTransport()
        activate_dynamic_talkgroup(
            transport,
            dmr_id=2632198,
            talkgroup=91,
            timeslot=2,
            sleep=lambda _seconds: None,
        )
        self.assertEqual(8, len(transport.sent))
        self.assertTrue(all(len(packet) == 55 for packet in transport.sent))

    def test_private_call_cannot_be_used_as_dynamic_tg_activation(self):
        transport = FakeTransport()
        with self.assertRaisesRegex(ValueError, "nur für Gruppenrufe"):
            activate_dynamic_talkgroup(
                transport,
                dmr_id=2632198,
                talkgroup=9990,
                timeslot=2,
                call_type="private",
                sleep=lambda _seconds: None,
            )
        self.assertEqual([], transport.sent)

    def test_target_validation(self):
        self.assertEqual((91, 2), validate_receive_target(91, 2))
        with self.assertRaises(ValueError):
            validate_receive_target(0, 2)
        with self.assertRaises(ValueError):
            validate_receive_target(91, 3)


if __name__ == "__main__":
    unittest.main()
