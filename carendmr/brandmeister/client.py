"""Synchroner, klar testbarer BrandMeister-Login-Client."""

from __future__ import annotations

from dataclasses import dataclass

from carendmr.network import (
    NetworkReceiveTimeout,
    PacketLogger,
    UdpTransport,
    identify_ascii_packet,
    resolve_udp_endpoint,
)

from .config import BrandMeisterConfig
from .protocol import (
    LoginState,
    build_auth_packet,
    build_close_packet,
    build_config_packet,
    build_login_packet,
    build_ping_packet,
    extract_challenge,
    is_master_ack,
    is_master_nak,
    is_master_pong,
)


class BrandMeisterLoginError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class BrandMeisterLoginResult:
    host: str
    address: str
    port: int
    dmr_id: int
    callsign: str
    state: LoginState


class BrandMeisterClient:
    def __init__(
        self,
        config: BrandMeisterConfig,
        *,
        transport_factory=UdpTransport,
        packet_logger: PacketLogger | None = None,
    ) -> None:
        config.validate()
        self.config = config
        self.transport_factory = transport_factory
        self.packet_logger = packet_logger or PacketLogger(enabled=False)
        self.transport = None
        self.state = LoginState.DISCONNECTED
        self.endpoint = None

    def login(self) -> BrandMeisterLoginResult:
        self.endpoint = resolve_udp_endpoint(
            self.config.host,
            self.config.port,
        )
        self.transport = self.transport_factory(
            self.endpoint,
            timeout_seconds=self.config.timeout_seconds,
        )
        self.transport.open()

        try:
            self.state = LoginState.WAITING_LOGIN_ACK
            self._send("RPTL", build_login_packet(self.config.dmr_id))
            first = self._receive_ack(
                "Der BrandMeister-Master hat das Login nicht bestätigt."
            )
            challenge = extract_challenge(first)

            self.state = LoginState.WAITING_AUTH_ACK
            self._send(
                "RPTK",
                build_auth_packet(
                    self.config.dmr_id,
                    challenge,
                    self.config.password,
                )
            )
            self._receive_ack(
                "Das BrandMeister-Hotspot-Passwort wurde nicht bestätigt."
            )

            self.state = LoginState.WAITING_CONFIG_ACK
            self._send(
                "RPTC",
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
                )
            )
            self._receive_ack(
                "Der BrandMeister-Master hat die Stationsdaten nicht bestätigt."
            )

            self.state = LoginState.CONNECTED
            return BrandMeisterLoginResult(
                host=self.config.host,
                address=self.endpoint.address_text,
                port=self.config.port,
                dmr_id=self.config.dmr_id,
                callsign=self.config.callsign,
                state=self.state,
            )
        except Exception:
            if self.state is not LoginState.REJECTED:
                self.state = LoginState.DISCONNECTED
            self.close(send_close=False)
            raise

    def ping(self) -> bool:
        if self.state is not LoginState.CONNECTED or self.transport is None:
            raise BrandMeisterLoginError(
                "Ein Ping ist erst nach erfolgreicher Anmeldung möglich."
            )
        self._send("RPTPING", build_ping_packet(self.config.dmr_id))
        reply = self._receive()
        if is_master_nak(reply):
            self.state = LoginState.REJECTED
            raise BrandMeisterLoginError(
                "Der Master erkennt die angemeldete Station nicht mehr."
            )
        return is_master_pong(reply, self.config.dmr_id)

    def close(self, *, send_close: bool = True) -> None:
        transport, self.transport = self.transport, None
        if transport is not None:
            if send_close and self.state is LoginState.CONNECTED:
                try:
                    packet = build_close_packet(self.config.dmr_id)
                    self.packet_logger.log("TX", "BrandMeister", "RPTCL", packet)
                    transport.send(packet)
                except Exception:
                    pass
            transport.close()
        self.state = LoginState.DISCONNECTED

    def _send(self, packet_name: str, packet: bytes) -> None:
        self.packet_logger.log("TX", "BrandMeister", packet_name, packet)
        self.transport.send(packet)

    def _receive(self) -> bytes:
        packet = self.transport.receive()
        self.packet_logger.log(
            "RX",
            "BrandMeister",
            identify_ascii_packet(packet),
            packet,
        )
        return packet

    def _receive_ack(self, message: str) -> bytes:
        try:
            packet = self._receive()
        except NetworkReceiveTimeout as exc:
            raise BrandMeisterLoginError(
                f"{message} Das Zeitlimit wurde überschritten."
            ) from exc
        if is_master_nak(packet):
            self.state = LoginState.REJECTED
            raise BrandMeisterLoginError(
                f"{message} Der Server antwortete mit MSTNAK."
            )
        if not is_master_ack(packet):
            raise BrandMeisterLoginError(
                f"{message} Es kam eine unerwartete Antwort."
            )
        return packet
