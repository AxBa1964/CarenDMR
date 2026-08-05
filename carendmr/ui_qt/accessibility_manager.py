"""Zentrale Accessibility-Steuerung für die Qt-Oberfläche.

Der Manager erzeugt keine eigene Sprache. Er bündelt ausschließlich native
Qt-Accessibility-Meldungen und die funkfachliche Formatierung.
"""
from __future__ import annotations

from typing import Any

from carendmr.ui_qt.accessibility_announcer import NativeAccessibilityAnnouncer
from carendmr.ui_qt.accessibility_formatter import RadioAccessibilityFormatter


class AccessibilityManager:
    def __init__(self) -> None:
        self.announcer = NativeAccessibilityAnnouncer()
        self.formatter = RadioAccessibilityFormatter()
        self._last_radio_state: str | None = None

    def announce_operation_context(
        self,
        widget: Any,
        *,
        talkgroup: int,
        timeslot: int,
        call_type: str,
        state_label: str,
    ) -> None:
        self.announcer.announce(
            widget,
            self.formatter.operation_context(talkgroup, timeslot, call_type, state_label),
            channel="operation-context",
        )

    def announce_radio_state(self, widget: Any, state: str, *, force: bool = False) -> None:
        normalized = str(state).upper()
        if not force and normalized == self._last_radio_state:
            return
        self._last_radio_state = normalized
        messages = {
            "CONNECTED": "Verbunden.",
            "DISCONNECTED": "Verbindung getrennt.",
            "ERROR": "Verbindungsfehler.",
        }
        message = messages.get(normalized)
        if message:
            self.announcer.announce(widget, message, channel="radio-state", force=force)

    def announce_pending_talkgroup(self, widget: Any, value: str) -> None:
        if str(value).strip():
            self.announcer.announce(
                widget,
                self.formatter.pending_talkgroup(str(value)),
                channel="talkgroup-confirmation",
            )

    def announce_timeslot(self, widget: Any, timeslot: int) -> None:
        self.announcer.announce(widget, f"Timeslot {timeslot}.", channel="timeslot")

    def announce_call_type(self, widget: Any, call_type: str) -> None:
        self.announcer.announce(widget, f"{self.formatter.call_type(call_type)}.", channel="call-type")

    def announce_toggle(self, widget: Any, label: str, enabled: bool) -> None:
        state = "aktiviert" if enabled else "deaktiviert"
        self.announcer.announce(widget, f"{label} {state}.", channel=f"toggle:{label}")

    def announce_history_context(self, widget: Any, count: int) -> None:
        self.announcer.announce(
            widget,
            self.formatter.history_context(count),
            channel="history-context",
        )
