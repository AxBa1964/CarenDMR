"""Lokale, Qt-basierte Kanalübergabe zwischen TG-Monitor und CarenDMR."""
from __future__ import annotations

import json
from typing import Callable

from PySide6.QtCore import QIODevice
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from carendmr.domain import DmrChannel
from carendmr.ipc.protocol import decode_request, encode_request

CHANNEL_SERVER_NAME = "CarenDMR.ChannelControl.v1"
def _response(ok: bool, message: str) -> bytes:
    return (json.dumps({"ok": bool(ok), "message": str(message)}, ensure_ascii=False) + "\n").encode("utf-8")


class CarenDMRChannelServer:
    """QLocalServer im Qt-Hauptthread; greift nicht in Funk-/Audiokerne ein."""

    def __init__(self, handler: Callable[[DmrChannel], tuple[bool, str]]) -> None:
        self._handler = handler
        self._server = QLocalServer()
        self._server.newConnection.connect(self._accept_pending)

    @property
    def is_listening(self) -> bool:
        return self._server.isListening()

    def start(self) -> bool:
        # Entfernt nur einen verwaisten lokalen Server-Eintrag eines früheren Absturzes.
        QLocalServer.removeServer(CHANNEL_SERVER_NAME)
        return bool(self._server.listen(CHANNEL_SERVER_NAME))

    def close(self) -> None:
        self._server.close()
        QLocalServer.removeServer(CHANNEL_SERVER_NAME)

    def _accept_pending(self) -> None:
        while self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            if socket is None:
                return
            socket.waitForReadyRead(250)
            try:
                raw = bytes(socket.readAll()).strip()
                channel = decode_request(raw)
                ok, message = self._handler(channel)
            except Exception as error:
                ok, message = False, str(error)
            socket.write(_response(ok, message))
            socket.flush()
            socket.waitForBytesWritten(250)
            socket.disconnectFromServer()


def send_channel_to_carendmr(
    channel: DmrChannel,
    *,
    timeout_ms: int = 1200,
) -> tuple[bool, str]:
    """Sendet genau einen Kanal an eine laufende CarenDMR-Instanz."""
    payload = encode_request(channel)
    socket = QLocalSocket()
    socket.connectToServer(CHANNEL_SERVER_NAME, QIODevice.OpenModeFlag.ReadWrite)
    if not socket.waitForConnected(timeout_ms):
        return False, "CarenDMR läuft nicht oder die lokale Übergabe ist nicht erreichbar."
    if socket.write(payload) < 0:
        return False, "Kanal konnte nicht an CarenDMR gesendet werden."
    socket.flush()
    # QLocalSocket kann die Bytes bereits vollständig übertragen haben, bevor
    # waitForBytesWritten() aufgerufen wird. Dessen False-Rückgabe ist deshalb
    # kein belastbarer Sendefehler. Maßgeblich ist die Antwort von CarenDMR.
    socket.waitForBytesWritten(min(timeout_ms, 250))
    if not socket.waitForReadyRead(timeout_ms):
        return False, "CarenDMR hat nicht auf die Kanalübergabe geantwortet."
    try:
        response = json.loads(bytes(socket.readAll()).decode("utf-8"))
        return bool(response.get("ok")), str(response.get("message", ""))
    except Exception:
        return False, "Ungültige Antwort von CarenDMR."
