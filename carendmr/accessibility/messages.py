"""Zentrale verständliche Meldungen für technische Zustände."""

from __future__ import annotations

from carendmr.core.status import AppStatus


_STATUS_MESSAGES: dict[AppStatus, str] = {
    AppStatus.STARTING: "CarenDMR wird gestartet.",
    AppStatus.READY: "CarenDMR ist bereit.",
    AppStatus.CONNECTING: "Verbindung wird hergestellt.",
    AppStatus.CONNECTED: "Verbunden.",
    AppStatus.DISCONNECTED: "Verbindung getrennt.",
    AppStatus.RECEIVING: "Empfang.",
    AppStatus.TRANSMITTING: "Senden.",
    AppStatus.ERROR: "Ein Fehler ist aufgetreten.",
}


def message_for_status(
    status: AppStatus,
    detail: str | None = None,
) -> str:
    """Übersetzt einen technischen Zustand in eine verständliche Meldung."""
    base_message = _STATUS_MESSAGES[status]
    if detail:
        return f"{base_message} {detail}".strip()
    return base_message
