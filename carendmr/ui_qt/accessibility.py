"""Kompatibilitätsschicht für ältere Qt-UI-Aufrufe.

Neue Qt-Oberflächen verwenden ``AccessibilityManager``. Die Funktion
``announce`` bleibt für bestehende Imports vorübergehend erhalten.
"""
from __future__ import annotations

from typing import Any

from carendmr.ui_qt.accessibility_announcer import NativeAccessibilityAnnouncer

_DEFAULT_ANNOUNCER = NativeAccessibilityAnnouncer()


def announce(widget: Any, message: str) -> None:
    _DEFAULT_ANNOUNCER.announce(widget, message)
