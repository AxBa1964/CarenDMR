"""Native Qt-Ankündigungen ohne eigene Sprachausgabe."""
from __future__ import annotations

import time
from typing import Any


class NativeAccessibilityAnnouncer:
    """Sendet kurze Meldungen an Qt Accessibility und entprellt je Kanal."""

    def __init__(self, duplicate_window_seconds: float = 2.0) -> None:
        self.duplicate_window_seconds = float(duplicate_window_seconds)
        self._last_by_channel: dict[str, tuple[str, float]] = {}

    def announce(self, widget: Any, message: str, *, channel: str = "general", force: bool = False) -> None:
        text = str(message).strip()
        if not text or widget is None:
            return

        now = time.monotonic()
        previous_text, previous_at = self._last_by_channel.get(channel, ("", 0.0))
        if not force and text == previous_text and now - previous_at < self.duplicate_window_seconds:
            return
        self._last_by_channel[channel] = (text, now)

        try:
            from PySide6.QtGui import QAccessible, QAccessibleAnnouncementEvent

            event = QAccessibleAnnouncementEvent(widget, text)
            politeness_enum = getattr(QAccessible, "AnnouncementPoliteness", None)
            if politeness_enum is not None and hasattr(event, "setPoliteness"):
                politeness = getattr(politeness_enum, "Assertive", None)
                if politeness is not None:
                    event.setPoliteness(politeness)
            QAccessible.updateAccessibility(event)
            return
        except Exception:
            pass

        try:
            from PySide6.QtGui import QAccessible, QAccessibleEvent

            original_name = widget.accessibleName() if hasattr(widget, "accessibleName") else ""
            widget.setAccessibleName(text)
            event_enum = getattr(QAccessible, "Event", None)
            event_type = getattr(event_enum, "Alert", None) if event_enum is not None else None
            if event_type is None and event_enum is not None:
                event_type = getattr(event_enum, "NameChanged", None)
            if event_type is not None:
                QAccessible.updateAccessibility(QAccessibleEvent(widget, event_type))
            if hasattr(widget, "setAccessibleName"):
                widget.setAccessibleName(original_name)
        except Exception:
            return
