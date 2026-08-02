import inspect
import unittest
from dataclasses import FrozenInstanceError

from carendmr.brandmeister.dmrd import DmrdCallType, parse_dmrd_packet
from carendmr.brandmeister.parrot_profile import (
    LOCKED_PARROT_PROFILE,
    PARROT_DESTINATION_ID,
    PARROT_ECHO_CAP_SECONDS,
    PARROT_FIXTURE_SECONDS,
    PARROT_TIMESLOT,
    PARROT_TRANSMIT_CAP_SECONDS,
    LockedParrotTestProfile,
    ParrotSafetyError,
    ParrotTestPlan,
    build_locked_parrot_fixture,
    build_locked_parrot_test_plan,
)


class LockedParrotProfileTests(unittest.TestCase):
    SOURCE_ID = 0x010203
    REPEATER_ID = 0x01020304
    STREAM_ID = 0x11223344

    REFERENCE_PAYLOADS = tuple(
        bytes.fromhex(value)
        for value in (
            "4427024121a21ad01fd07041846d5d7f77fd757e33ac236806e009c11452040751",
            "b9e881526173002a6bb9e8815267f7d5dd57dfd173002a6bb9e881526173002a6b",
            "b9e881526173002a6bb9e881526130300110c91173002a6bb9e881526173002a6b",
            "b9e881526173002a6bb9e881526170911909074173002a6bb9e881526173002a6b",
            "b9e881526173002a6bb9e8815261703032e9c74173002a6bb9e881526173002a6b",
            "b9e881526173002a6bb9e8815261584b835bd07173002a6bb9e881526173002a6b",
            "b9e881526173002a6bb9e8815261100000000e2173002a6bb9e881526173002a6b",
            "4448029521121aa81fa070e184ad5d7f77fd757966b82050018005811c521d0762",
        )
    )

    def build(self):
        return build_locked_parrot_test_plan(
            source_id=self.SOURCE_ID,
            repeater_id=self.REPEATER_ID,
            stream_id=self.STREAM_ID,
            first_sequence=250,
        )

    def test_profile_is_exactly_private_9990_timeslot_two_with_fixed_caps(self):
        profile = LOCKED_PARROT_PROFILE
        self.assertEqual(PARROT_DESTINATION_ID, profile.destination_id)
        self.assertEqual(PARROT_TIMESLOT, profile.timeslot)
        self.assertIs(DmrdCallType.PRIVATE, profile.call_type)
        self.assertEqual(180.0, PARROT_TRANSMIT_CAP_SECONDS)
        self.assertEqual(15.0, PARROT_ECHO_CAP_SECONDS)
        self.assertEqual(PARROT_FIXTURE_SECONDS, self.build().transmit_seconds)

    def test_every_homebrew_packet_has_private_flag_byte_for_byte(self):
        plan = self.build()
        expected_flags = (0xE1, 0xD0, 0xC1, 0xC2, 0xC3, 0xC4, 0xC5, 0xE2)
        self.assertEqual(
            expected_flags,
            tuple(packet.to_bytes()[15] for packet in plan.fixture.packets),
        )
        for packet in plan.fixture.packets:
            self.assertEqual(PARROT_DESTINATION_ID, packet.destination_id)
            self.assertEqual(PARROT_TIMESLOT, packet.timeslot)
            self.assertIs(DmrdCallType.PRIVATE, packet.call_type)
            self.assertEqual(packet, parse_dmrd_packet(packet.to_bytes()))

    def test_link_control_and_bursts_are_pinned_to_private_reference_bytes(self):
        self.assertEqual(
            self.REFERENCE_PAYLOADS,
            tuple(packet.payload for packet in self.build().fixture.packets),
        )

    def test_runtime_api_has_no_target_timeslot_call_type_or_duration_inputs(self):
        parameters = inspect.signature(build_locked_parrot_test_plan).parameters
        forbidden = {
            "destination_id",
            "talkgroup",
            "timeslot",
            "call_type",
            "transmit_seconds",
            "echo_seconds",
            "duration",
        }
        self.assertFalse(forbidden.intersection(parameters))

    def test_plan_is_offline_immutable_and_has_no_execution_surface(self):
        plan = self.build()
        self.assertFalse(hasattr(plan, "send"))
        self.assertFalse(hasattr(plan, "execute"))
        with self.assertRaises(FrozenInstanceError):
            plan.transmit_seconds = 11

    def test_modified_profile_fails_closed(self):
        fixture = build_locked_parrot_fixture(
            source_id=self.SOURCE_ID,
            repeater_id=self.REPEATER_ID,
            stream_id=self.STREAM_ID,
        )
        with self.assertRaisesRegex(ParrotSafetyError, "verändert"):
            ParrotTestPlan(
                profile=LockedParrotTestProfile(destination_id=91),
                fixture=fixture,
                transmit_seconds=0.36,
                echo_observation_seconds=15.0,
            )

    def test_invalid_identifiers_and_sequences_fail_closed(self):
        defaults = {
            "source_id": self.SOURCE_ID,
            "repeater_id": self.REPEATER_ID,
            "stream_id": self.STREAM_ID,
            "first_sequence": 0,
        }
        for override in (
            {"source_id": 0},
            {"repeater_id": 0},
            {"stream_id": 0},
            {"first_sequence": -1},
            {"first_sequence": 256},
        ):
            with self.subTest(override=override), self.assertRaises(ValueError):
                build_locked_parrot_fixture(**(defaults | override))


if __name__ == "__main__":
    unittest.main()
