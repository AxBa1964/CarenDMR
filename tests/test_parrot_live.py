import unittest

from carendmr.accessibility import ParrotTestPhase
from carendmr.brandmeister.config import BrandMeisterConfig
from carendmr.brandmeister.parrot_live import (
    PACKET_INTERVAL_SECONDS,
    ParrotLiveError,
    execute_locked_parrot_once,
)
from carendmr.brandmeister.parrot_profile import build_locked_parrot_fixture
from carendmr.brandmeister.protocol import LoginState
from carendmr.network import NetworkReceiveTimeout
from carendmr.vocoder import PcmFrame


class FakeAnnouncer:
    def __init__(self):
        self.phases = []

    def announce(self, phase):
        self.phases.append(phase)


class FakeOutput:
    def __init__(self, **_):
        self.is_open = False
        self.samples = 0

    def start(self):
        self.is_open = True

    def write(self, samples):
        self.samples += len(samples)

    def close(self):
        self.is_open = False


class FakeDecoder:
    def decode(self, _word):
        return PcmFrame((1,) * 160, corrected_errors=0)

    def close(self):
        pass


class FakeTransport:
    def __init__(self, replies=(), fail_on_send=None):
        self.replies = list(replies)
        self.fail_on_send = fail_on_send
        self.sent = []
        self.timeouts = []
        self.closed = False

    def send(self, packet):
        if len(self.sent) == self.fail_on_send:
            raise OSError("controlled")
        self.sent.append(packet)
        return len(packet)

    def receive(self):
        if self.replies:
            return self.replies.pop(0)
        raise NetworkReceiveTimeout("none")

    def set_receive_timeout(self, seconds):
        self.timeouts.append(seconds)


class FakeClient:
    transport_instance = None

    def __init__(self, config):
        self.config = config
        self.transport = self.transport_instance
        self.state = LoginState.DISCONNECTED

    def login(self):
        self.state = LoginState.CONNECTED

    def close(self):
        if self.transport is not None:
            self.transport.closed = True
        self.transport = None
        self.state = LoginState.DISCONNECTED


class Clock:
    def __init__(self, step=0.01):
        self.value = -step
        self.step = step

    def __call__(self):
        self.value += self.step
        return self.value


class ParrotLiveTests(unittest.TestCase):
    def setUp(self):
        self.config = BrandMeisterConfig(
            host="example.invalid",
            port=62031,
            dmr_id=0x010203,
            password="non-sensitive-test",
            callsign="N0TEST",
        )
        self.echo = build_locked_parrot_fixture(
            source_id=0x010203,
            repeater_id=0x010203,
            stream_id=0x11223344,
        ).to_bytes()

    def execute(self, transport, *, clock=None):
        FakeClient.transport_instance = transport
        announcer = FakeAnnouncer()
        sleeps = []
        result = execute_locked_parrot_once(
            self.config,
            announcer=announcer,
            client_factory=FakeClient,
            output_factory=FakeOutput,
            decoder_factory=FakeDecoder,
            sequence_factory=lambda: 0,
            stream_factory=lambda: 0x11223344,
            monotonic=clock or Clock(),
            sleep=sleeps.append,
        )
        return result, announcer, sleeps

    def test_exactly_one_private_sequence_then_echo_audio_and_cleanup(self):
        transport = FakeTransport(self.echo)
        result, announcer, sleeps = self.execute(transport)

        self.assertEqual(8, len(transport.sent))
        self.assertEqual(8, result.sent_packets)
        self.assertTrue(all(packet[15] & 0x40 for packet in transport.sent))
        self.assertTrue(all(packet[8:11] == (9990).to_bytes(3, "big") for packet in transport.sent))
        self.assertEqual([PACKET_INTERVAL_SECONDS] * 7 + [0.25], sleeps)
        self.assertLessEqual(result.transmit_elapsed_seconds, 10.0)
        self.assertEqual(6, result.echo_voice_bursts)
        self.assertEqual(18, result.decoded_codewords)
        self.assertEqual(2880, result.output_samples)
        self.assertTrue(result.echo_received)
        self.assertFalse(result.timed_out)
        self.assertTrue(result.closed)
        self.assertTrue(transport.closed)
        self.assertEqual(
            [
                ParrotTestPhase.START,
                ParrotTestPhase.TRANSMIT,
                ParrotTestPhase.ECHO,
                ParrotTestPhase.SUCCESS,
            ],
            announcer.phases,
        )

    def test_send_failure_has_no_retry_and_closes(self):
        transport = FakeTransport(fail_on_send=3)
        FakeClient.transport_instance = transport
        announcer = FakeAnnouncer()

        with self.assertRaises(ParrotLiveError) as caught:
            execute_locked_parrot_once(
                self.config,
                announcer=announcer,
                client_factory=FakeClient,
                output_factory=FakeOutput,
                decoder_factory=FakeDecoder,
                sequence_factory=lambda: 0,
                stream_factory=lambda: 1,
                monotonic=Clock(),
                sleep=lambda _: None,
            )

        self.assertEqual(3, len(transport.sent))
        self.assertEqual(3, caught.exception.sent_packets)
        self.assertTrue(caught.exception.closed)
        self.assertEqual(ParrotTestPhase.FAILURE, announcer.phases[-1])

    def test_echo_timeout_is_bounded_and_not_retried(self):
        transport = FakeTransport()
        result, announcer, _ = self.execute(transport, clock=Clock(step=1.0))

        self.assertEqual(8, len(transport.sent))
        self.assertTrue(result.timed_out)
        self.assertFalse(result.echo_received)
        self.assertEqual(ParrotTestPhase.TIMEOUT, announcer.phases[-1])
        self.assertTrue(all(0 < value <= 0.5 for value in transport.timeouts))

    def test_hard_transmit_clock_fails_before_cap_can_be_crossed(self):
        transport = FakeTransport()
        FakeClient.transport_instance = transport

        with self.assertRaises(ParrotLiveError) as caught:
            execute_locked_parrot_once(
                self.config,
                announcer=FakeAnnouncer(),
                client_factory=FakeClient,
                output_factory=FakeOutput,
                decoder_factory=FakeDecoder,
                sequence_factory=lambda: 0,
                stream_factory=lambda: 1,
                monotonic=Clock(step=11.0),
                sleep=lambda _: None,
            )

        self.assertEqual(0, caught.exception.sent_packets)
        self.assertEqual(0, len(transport.sent))
        self.assertTrue(caught.exception.closed)


if __name__ == "__main__":
    unittest.main()
