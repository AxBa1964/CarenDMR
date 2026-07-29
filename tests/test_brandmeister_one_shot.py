import unittest

from carendmr.brandmeister import BrandMeisterConfig
from carendmr.brandmeister.protocol import LoginState
from carendmr.network import NetworkReceiveTimeout
from tools.brandmeister_one_shot import (
    MONITOR_SECONDS,
    PACKET_INTERVAL_SECONDS,
    OneShotExecutionError,
    OneShotSafetyError,
    execute_one_shot,
)


class FakeTransport:
    def __init__(self, *, fail_on_send=None, replies=()):
        self.fail_on_send = fail_on_send
        self.replies = list(replies)
        self.sent = []
        self.closed = False

    def send(self, packet):
        if len(self.sent) == self.fail_on_send:
            raise OSError("controlled failure")
        self.sent.append(packet)
        return len(packet)

    def receive(self):
        if self.replies:
            return self.replies.pop(0)
        raise NetworkReceiveTimeout("done")


class FakeClient:
    transport_instance = None

    def __init__(self, config):
        self.config = config
        self.transport = self.transport_instance
        self.state = LoginState.DISCONNECTED

    def login(self):
        self.state = LoginState.CONNECTED

    def close(self):
        self.transport.closed = True
        self.transport = None
        self.state = LoginState.DISCONNECTED


class OneShotTests(unittest.TestCase):
    def setUp(self):
        self.config = BrandMeisterConfig(
            host="example.invalid",
            port=62031,
            dmr_id=0x010203,
            password="private",
            callsign="TEST",
        )

    def run_one_shot(self, transport, *, clock_values=(0.0, 1.0)):
        FakeClient.transport_instance = transport
        clock = iter(clock_values)
        sleeps = []
        result = execute_one_shot(
            self.config,
            client_factory=FakeClient,
            sleep=sleeps.append,
            monotonic=lambda: next(clock),
            monitor_seconds=0.5,
            sequence_factory=lambda: 7,
            stream_factory=lambda: 0x11223344,
        )
        return result, sleeps

    def test_sends_exactly_eight_packets_once_with_seven_intervals(self):
        transport = FakeTransport()

        result, sleeps = self.run_one_shot(transport)

        self.assertEqual(8, result.sent_packets)
        self.assertTrue(result.sequence_complete)
        self.assertEqual(8, len(transport.sent))
        self.assertEqual([PACKET_INTERVAL_SECONDS] * 7, sleeps)
        self.assertTrue(all(packet.startswith(b"DMRD") for packet in transport.sent))
        self.assertTrue(result.closed)
        self.assertTrue(transport.closed)

    def test_send_error_fails_closed_without_retry(self):
        transport = FakeTransport(fail_on_send=3)
        FakeClient.transport_instance = transport

        with self.assertRaises(OneShotExecutionError) as caught:
            execute_one_shot(
                self.config,
                client_factory=FakeClient,
                sleep=lambda _: None,
                monotonic=lambda: 0.0,
                monitor_seconds=0.5,
                sequence_factory=lambda: 7,
                stream_factory=lambda: 0x11223344,
            )

        self.assertEqual(3, len(transport.sent))
        self.assertEqual(3, caught.exception.sent_packets)
        self.assertTrue(caught.exception.authenticated)
        self.assertTrue(caught.exception.closed)
        self.assertTrue(transport.closed)

    def test_monitor_classifies_valid_invalid_and_control_packets(self):
        reference = []
        collecting = FakeTransport()
        result, _ = self.run_one_shot(collecting)
        reference.extend(collecting.sent)
        transport = FakeTransport(
            replies=(reference[1], b"DMRDshort", b"MSTPONG-control")
        )

        result, _ = self.run_one_shot(
            transport,
            clock_values=(0.0, 0.1, 0.2, 0.3, 1.0),
        )

        self.assertEqual(3, result.monitor.total)
        self.assertEqual(1, result.monitor.dmrd)
        self.assertEqual(1, result.monitor.target_dmrd)
        self.assertEqual(1, result.monitor.invalid_dmrd)
        self.assertEqual(1, result.monitor.other_control)

    def test_monitor_window_cannot_exceed_fixed_bound(self):
        FakeClient.transport_instance = FakeTransport()

        with self.assertRaises(OneShotSafetyError):
            execute_one_shot(
                self.config,
                client_factory=FakeClient,
                monitor_seconds=MONITOR_SECONDS + 0.1,
            )

    def test_dmr_source_id_must_fit_three_bytes(self):
        invalid = BrandMeisterConfig(
            host="example.invalid",
            port=62031,
            dmr_id=0x1000000,
            password="private",
            callsign="TEST",
        )

        with self.assertRaisesRegex(OneShotSafetyError, "Quellfeld"):
            execute_one_shot(invalid, client_factory=FakeClient)

if __name__ == "__main__":
    unittest.main()
