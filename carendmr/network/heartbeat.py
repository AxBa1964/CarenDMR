"""Deterministische Heartbeat-Steuerung ohne eigenen Hintergrund-Thread."""

from __future__ import annotations

from collections.abc import Callable


class HeartbeatController:
    """Entscheidet, wann der nächste Heartbeat fällig ist.

    Der Controller versendet selbst keine protokollspezifischen Daten. Das
    spätere BrandMeister-Modul liefert dafür eine Callback-Funktion.
    """

    def __init__(
        self,
        interval_seconds: float,
        send_callback: Callable[[], None],
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError(
                "Das Heartbeat-Intervall muss größer als null sein."
            )
        self.interval_seconds = interval_seconds
        self.send_callback = send_callback
        self._last_sent_at: float | None = None
        self._enabled = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def last_sent_at(self) -> float | None:
        return self._last_sent_at

    def start(self, now: float) -> None:
        self._enabled = True
        self._last_sent_at = now

    def stop(self) -> None:
        self._enabled = False
        self._last_sent_at = None

    def tick(self, now: float) -> bool:
        """Sendet bei Fälligkeit genau einen Heartbeat."""
        if not self._enabled or self._last_sent_at is None:
            return False
        if now - self._last_sent_at < self.interval_seconds:
            return False
        self.send_callback()
        self._last_sent_at = now
        return True
