import socket
import unittest

from carendmr.network import (
    NetworkReceiveTimeout,
    NetworkTransportError,
    ResolvedEndpoint,
    UdpTransport,
)


class FakeSocket:
    def __init__(self):
        self.timeout = None
        self.connected_to = None
        self.sent = []
        self.receive_value = b"reply"
        self.receive_error = None
        self.closed = False

    def settimeout(self, value):
        self.timeout = value

    def connect(self, sockaddr):
        self.connected_to = sockaddr

    def send(self, payload):
        self.sent.append(payload)
        return len(payload)

    def recv(self, max_bytes):
        if self.receive_error:
            raise self.receive_error
        return self.receive_value[:max_bytes]

    def close(self):
        self.closed = True


class UdpTransportTests(unittest.TestCase):
    def setUp(self):
        self.endpoint = ResolvedEndpoint(
            host="example.net",
            port=62031,
            family=socket.AF_INET,
            sockaddr=("192.0.2.1", 62031),
        )
        self.fake = FakeSocket()
        self.transport = UdpTransport(
            self.endpoint,
            timeout_seconds=2.0,
            socket_factory=lambda *args: self.fake,
        )

    def test_open_send_receive_close(self):
        self.transport.open()

        sent = self.transport.send(b"hello")
        received = self.transport.receive()
        self.transport.close()

        self.assertEqual(5, sent)
        self.assertEqual(b"reply", received)
        self.assertEqual(("192.0.2.1", 62031), self.fake.connected_to)
        self.assertEqual(2.0, self.fake.timeout)
        self.assertTrue(self.fake.closed)

    def test_send_requires_open_transport(self):
        with self.assertRaisesRegex(NetworkTransportError, "nicht geöffnet"):
            self.transport.send(b"hello")

    def test_empty_packet_is_rejected(self):
        self.transport.open()
        with self.assertRaisesRegex(ValueError, "leeres UDP-Paket"):
            self.transport.send(b"")

    def test_receive_timeout_is_translated(self):
        self.transport.open()
        self.fake.receive_error = socket.timeout()

        with self.assertRaisesRegex(
            NetworkReceiveTimeout,
            "nicht geantwortet",
        ):
            self.transport.receive()


if __name__ == "__main__":
    unittest.main()
