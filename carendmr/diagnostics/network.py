"""Verständliche Netzwerkdiagnose ohne BrandMeister-Anmeldung."""

from __future__ import annotations

from carendmr.network import (
    NetworkConfig,
    UdpTransport,
    resolve_udp_endpoint,
)

from .models import DiagnosticResult, DiagnosticStatus


class NetworkDiagnostics:
    def __init__(self, config: NetworkConfig) -> None:
        self.config = config

    def run(self) -> tuple[DiagnosticResult, ...]:
        results: list[DiagnosticResult] = []

        try:
            self.config.validate()
        except ValueError as exc:
            return (
                DiagnosticResult(
                    check_id="network_config",
                    status=DiagnosticStatus.ERROR,
                    summary="Die Netzwerk-Konfiguration ist ungültig.",
                    action=str(exc),
                ),
            )

        results.append(
            DiagnosticResult(
                check_id="network_config",
                status=DiagnosticStatus.OK,
                summary=(
                    f"Netzwerk-Konfiguration für {self.config.host}:"
                    f"{self.config.port} ist gültig."
                ),
            )
        )

        try:
            endpoint = resolve_udp_endpoint(
                self.config.host,
                self.config.port,
            )
        except OSError as exc:
            results.append(
                DiagnosticResult(
                    check_id="network_dns",
                    status=DiagnosticStatus.ERROR,
                    summary="Der Servername konnte nicht aufgelöst werden.",
                    action=(
                        f"{exc} Bitte prüfen Sie Servername und "
                        "Internetverbindung."
                    ),
                )
            )
            return tuple(results)

        results.append(
            DiagnosticResult(
                check_id="network_dns",
                status=DiagnosticStatus.OK,
                summary=(
                    f"Servername aufgelöst: {endpoint.address_text} "
                    f"über {endpoint.family_name}."
                ),
            )
        )

        transport = UdpTransport(
            endpoint,
            timeout_seconds=self.config.timeout_seconds,
        )
        try:
            transport.open()
        except Exception as exc:
            results.append(
                DiagnosticResult(
                    check_id="network_udp",
                    status=DiagnosticStatus.ERROR,
                    summary="Der lokale UDP-Netzwerkkanal konnte nicht geöffnet werden.",
                    action=(
                        f"{exc} Bitte prüfen Sie Firewall und "
                        "Netzwerkverbindung."
                    ),
                )
            )
        else:
            results.append(
                DiagnosticResult(
                    check_id="network_udp",
                    status=DiagnosticStatus.OK,
                    summary=(
                        "Der lokale UDP-Netzwerkkanal konnte geöffnet werden."
                    ),
                    action=(
                        "Eine Antwort des BrandMeister-Servers wird erst mit "
                        "der Anmeldung in einer späteren Version geprüft."
                    ),
                )
            )
        finally:
            transport.close()

        return tuple(results)
