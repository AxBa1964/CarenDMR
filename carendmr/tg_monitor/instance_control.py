"""Einzelinstanz-Schutz für den eigenständigen TG-Monitor."""
from __future__ import annotations

from PySide6.QtCore import QIODevice
from PySide6.QtNetwork import QLocalServer, QLocalSocket

TG_MONITOR_INSTANCE_SERVER = "CarenDMR.TGMonitor.Instance.v1"


def is_tg_monitor_running(timeout_ms: int = 200) -> bool:
    socket = QLocalSocket()
    socket.connectToServer(TG_MONITOR_INSTANCE_SERVER, QIODevice.OpenModeFlag.ReadWrite)
    connected = socket.waitForConnected(timeout_ms)
    if connected:
        socket.disconnectFromServer()
    return bool(connected)


def acquire_tg_monitor_instance() -> QLocalServer | None:
    """Liefert einen gehaltenen lokalen Server oder None bei laufender Instanz."""
    if is_tg_monitor_running():
        return None

    # Nur nach erfolglosem Verbindungsversuch darf ein verwaister Eintrag
    # eines früher abgestürzten Prozesses entfernt werden.
    QLocalServer.removeServer(TG_MONITOR_INSTANCE_SERVER)
    server = QLocalServer()
    if not server.listen(TG_MONITOR_INSTANCE_SERVER):
        return None
    return server


def send_tg_monitor_command(command: str, timeout_ms: int = 300) -> bool:
    socket = QLocalSocket()
    socket.connectToServer(TG_MONITOR_INSTANCE_SERVER, QIODevice.OpenModeFlag.ReadWrite)
    if not socket.waitForConnected(timeout_ms):
        return False
    payload = (str(command).strip().lower() + "\n").encode("utf-8")
    if socket.write(payload) < 0:
        return False
    socket.flush()
    socket.waitForBytesWritten(timeout_ms)
    socket.disconnectFromServer()
    return True
