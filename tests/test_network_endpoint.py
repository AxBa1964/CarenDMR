import socket
import unittest
from unittest.mock import patch

from carendmr.network import resolve_udp_endpoint


class NetworkEndpointTests(unittest.TestCase):
    @patch("carendmr.network.endpoint.socket.getaddrinfo")
    def test_prefers_ipv4_when_both_are_available(self, getaddrinfo):
        getaddrinfo.return_value = [
            (
                socket.AF_INET6,
                socket.SOCK_DGRAM,
                socket.IPPROTO_UDP,
                "",
                ("2001:db8::1", 62031, 0, 0),
            ),
            (
                socket.AF_INET,
                socket.SOCK_DGRAM,
                socket.IPPROTO_UDP,
                "",
                ("192.0.2.10", 62031),
            ),
        ]

        endpoint = resolve_udp_endpoint("master.example.net", 62031)

        self.assertEqual(socket.AF_INET, endpoint.family)
        self.assertEqual("192.0.2.10", endpoint.address_text)

    @patch("carendmr.network.endpoint.socket.getaddrinfo")
    def test_dns_failure_has_readable_message(self, getaddrinfo):
        getaddrinfo.side_effect = socket.gaierror("failure")

        with self.assertRaisesRegex(OSError, "konnte nicht aufgelöst"):
            resolve_udp_endpoint("invalid.example", 62031)


if __name__ == "__main__":
    unittest.main()
