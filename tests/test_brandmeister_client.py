import socket
import unittest
from unittest.mock import patch

from carendmr.brandmeister import (
    BrandMeisterClient,
    BrandMeisterConfig,
    BrandMeisterLoginError,
    LoginState,
)
from carendmr.brandmeister.protocol import (
    build_auth_packet,
    build_close_packet,
    build_config_packet,
    build_login_packet,
    build_options_packet,
    build_ping_packet,
)
from carendmr.network import ResolvedEndpoint


class FakeTransport:
    instances = []
    replies = []

    def __init__(self, endpoint, timeout_seconds):
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds
        self.sent = []
        self.closed = False
        FakeTransport.instances.append(self)

    def open(self):
        pass

    def send(self, packet):
        self.sent.append(packet)
        return len(packet)

    def receive(self):
        if not FakeTransport.replies:
            raise AssertionError("Keine Testantwort vorbereitet")
        return FakeTransport.replies.pop(0)

    def close(self):
        self.closed = True


class RecordingPacketLogger:
    def __init__(self):
        self.entries = []

    def log(self, direction, protocol, packet_name, packet):
        self.entries.append((direction, protocol, packet_name, packet))


class BrandMeisterClientTests(unittest.TestCase):
    def setUp(self):
        FakeTransport.instances = []
        FakeTransport.replies = []
        self.config = BrandMeisterConfig(
            host="master.example.net",
            port=62031,
            dmr_id=2620000,
            password="secret",
            callsign="DO1DPL",
        )
        self.endpoint = ResolvedEndpoint(
            host=self.config.host,
            port=self.config.port,
            family=socket.AF_INET,
            sockaddr=("192.0.2.1", self.config.port),
        )

    @patch("carendmr.brandmeister.client.resolve_udp_endpoint")
    def test_complete_login_ping_and_close(self, resolve):
        resolve.return_value = self.endpoint
        challenge = bytes.fromhex("11223344")
        suffix = self.config.dmr_id.to_bytes(4, "big")
        FakeTransport.replies = [
            b"RPTACK" + challenge,
            b"RPTACK",
            b"RPTACK",
            b"MSTPONG" + suffix,
        ]
        client = BrandMeisterClient(
            self.config,
            transport_factory=FakeTransport,
        )

        result = client.login()
        transport = FakeTransport.instances[0]

        self.assertEqual(LoginState.CONNECTED, result.state)
        self.assertEqual(
            [
                build_login_packet(self.config.dmr_id),
                build_auth_packet(
                    self.config.dmr_id,
                    challenge,
                    self.config.password,
                ),
                build_config_packet(
                    dmr_id=self.config.dmr_id,
                    callsign=self.config.callsign,
                    frequency_hz=self.config.frequency_hz,
                    latitude=self.config.latitude,
                    longitude=self.config.longitude,
                    location=self.config.location,
                    description=self.config.description,
                    url=self.config.url,
                    software_id=self.config.software_id,
                    package_id=self.config.package_id,
                ),
                build_options_packet(self.config.dmr_id, self.config.options),
            ],
            transport.sent,
        )

        self.assertTrue(client.ping())
        self.assertEqual(build_ping_packet(self.config.dmr_id), transport.sent[-1])

        client.close()
        self.assertEqual(build_close_packet(self.config.dmr_id), transport.sent[-1])
        self.assertTrue(transport.closed)

    @patch("carendmr.brandmeister.client.resolve_udp_endpoint")
    def test_master_nak_is_reported(self, resolve):
        resolve.return_value = self.endpoint
        FakeTransport.replies = [b"MSTNAK"]
        client = BrandMeisterClient(
            self.config,
            transport_factory=FakeTransport,
        )

        with self.assertRaisesRegex(BrandMeisterLoginError, "MSTNAK"):
            client.login()

        self.assertTrue(FakeTransport.instances[0].closed)

    @patch("carendmr.brandmeister.client.resolve_udp_endpoint")
    def test_packet_logger_records_login_traffic(self, resolve):
        resolve.return_value = self.endpoint
        challenge = bytes.fromhex("11223344")
        FakeTransport.replies = [
            b"RPTACK" + challenge,
            b"RPTACK",
            b"MSTNAK",
        ]
        logger = RecordingPacketLogger()
        client = BrandMeisterClient(
            self.config,
            transport_factory=FakeTransport,
            packet_logger=logger,
        )

        with self.assertRaises(BrandMeisterLoginError):
            client.login()

        summary = [(entry[0], entry[2]) for entry in logger.entries]
        self.assertEqual(
            [
                ("TX", "RPTL"),
                ("RX", "RPTACK"),
                ("TX", "RPTK"),
                ("RX", "RPTACK"),
                ("TX", "RPTC"),
                ("RX", "MSTNAK"),
            ],
            summary,
        )


if __name__ == "__main__":
    unittest.main()
