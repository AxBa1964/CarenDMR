import socket
import unittest
from unittest.mock import patch

from carendmr.diagnostics import DiagnosticStatus, NetworkDiagnostics
from carendmr.network import NetworkConfig


class FakeSocket:
    def settimeout(self, value):
        pass

    def connect(self, sockaddr):
        pass

    def close(self):
        pass


class NetworkDiagnosticsTests(unittest.TestCase):
    @patch("carendmr.network.endpoint.socket.getaddrinfo")
    @patch(
        "carendmr.diagnostics.network.UdpTransport",
    )
    def test_successful_local_network_diagnosis(
        self,
        transport_class,
        getaddrinfo,
    ):
        getaddrinfo.return_value = [
            (
                socket.AF_INET,
                socket.SOCK_DGRAM,
                socket.IPPROTO_UDP,
                "",
                ("192.0.2.1", 62031),
            )
        ]
        transport = transport_class.return_value
        transport.open.return_value = None

        results = NetworkDiagnostics(
            NetworkConfig(host="master.example.net")
        ).run()

        self.assertEqual(
            [DiagnosticStatus.OK] * 3,
            [result.status for result in results],
        )
        transport.close.assert_called_once()

    @patch("carendmr.network.endpoint.socket.getaddrinfo")
    def test_dns_failure_is_reported(self, getaddrinfo):
        getaddrinfo.side_effect = socket.gaierror("failure")

        results = NetworkDiagnostics(
            NetworkConfig(host="invalid.example")
        ).run()

        self.assertEqual(DiagnosticStatus.ERROR, results[-1].status)
        self.assertIn("Internetverbindung", results[-1].spoken_text())


if __name__ == "__main__":
    unittest.main()
