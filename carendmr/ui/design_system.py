"""Zentrales visuelles Designsystem für CarenDMR.

Die Gestaltung folgt nicht dekorativen Einzelentscheidungen, sondern vier
semantischen Elementklassen:

* Information: zeigt Zustand, ist nicht bedienbar.
* Eingabe: nimmt Werte entgegen.
* Auswahl: wählt genau eine Option.
* Aktion: löst einen Vorgang aus.

Damit erkennt ein sehender Benutzer bereits an Form, Farbe und Verhalten, was
ein Element tut. Die fachliche Bedienlogik bleibt davon vollständig getrennt.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final


class ElementKind(str, Enum):
    INFORMATION = "information"
    INPUT = "input"
    SELECTION = "selection"
    ACTION = "action"


@dataclass(frozen=True)
class Palette:
    background: str = "#0B1220"
    card: str = "#111C2E"
    card_alt: str = "#18263A"
    card_border: str = "#263A55"
    text: str = "#F4F7FB"
    muted: str = "#8FA3BB"
    cyan: str = "#55D7FF"

    # Semantische Farben
    information: str = "#18263A"
    input_bg: str = "#F2F5F8"
    input_text: str = "#1A2433"
    input_disabled_bg: str = "#28374B"
    input_disabled_text: str = "#A9B5C4"
    selection: str = "#2F80ED"
    selection_hover: str = "#3E8EF4"
    selection_inactive: str = "#1B2A40"
    selection_disabled: str = "#26364B"
    action: str = "#168457"
    action_hover: str = "#1C9967"
    critical: str = "#D94141"
    critical_hover: str = "#EB5252"
    transmit: str = "#C73535"
    disabled: str = "#666D78"
    disabled_text: str = "#E0E3E7"
    focus: str = "#55D7FF"
    focus_inner: str = "#FFFFFF"
    success: str = "#168457"
    warning: str = "#F2C94C"
    error: str = "#D94141"


PALETTE: Final = Palette()

# Abstände und Größen werden zentral gehalten, damit neue Ansichten dieselbe
# visuelle Sprache verwenden.
SPACE_XS: Final = 4
SPACE_SM: Final = 8
SPACE_MD: Final = 12
SPACE_LG: Final = 16
SPACE_XL: Final = 20

FOCUS_THICKNESS: Final = 4
RESTING_BORDER_THICKNESS: Final = 1
CONTROL_BORDER_WIDTH: Final = 1

FONT_FAMILY: Final = "Segoe UI"
FONT_MONO: Final = "Consolas"

FONT_SMALL: Final = (FONT_FAMILY, 9)
FONT_SMALL_BOLD: Final = (FONT_FAMILY, 9, "bold")
FONT_BODY: Final = (FONT_FAMILY, 10)
FONT_BODY_BOLD: Final = (FONT_FAMILY, 10, "bold")
FONT_CONTROL: Final = (FONT_FAMILY, 12, "bold")
FONT_ACTION: Final = (FONT_FAMILY, 13, "bold")
FONT_PTT: Final = (FONT_FAMILY, 18, "bold")
FONT_VALUE: Final = (FONT_FAMILY, 22, "bold")


def legacy_color_map() -> dict[str, str]:
    """Kompatibilitätsabbildung für bestehende UI-Bereiche.

    Neue Komponenten sollen die semantischen Namen aus :class:`Palette`
    verwenden. Die bestehende Oberfläche kann schrittweise migriert werden.
    """

    return {
        "background": PALETTE.background,
        "card": PALETTE.card,
        "card_alt": PALETTE.card_alt,
        "text": PALETTE.text,
        "muted": PALETTE.muted,
        "blue": PALETTE.selection,
        "blue_dark": "#1F65C1",
        "green": "#38D996",
        "green_dark": PALETTE.action,
        "cyan": PALETTE.cyan,
        "yellow": PALETTE.warning,
        "red": PALETTE.critical,
    }


def focus_options(active: bool) -> dict[str, object]:
    """Einheitlicher, deutlich sichtbarer Tastaturfokus für Tk-Widgets."""

    return {
        "highlightthickness": FOCUS_THICKNESS if active else RESTING_BORDER_THICKNESS,
        "highlightbackground": PALETTE.focus if active else PALETTE.card_border,
        "highlightcolor": PALETTE.focus,
    }


def input_options(*, enabled: bool = True) -> dict[str, object]:
    """Darstellung eines Eingabefeldes."""

    if enabled:
        return {
            "bg": PALETTE.input_bg,
            "fg": PALETTE.input_text,
            "insertbackground": PALETTE.input_text,
            "disabledbackground": PALETTE.input_disabled_bg,
            "disabledforeground": PALETTE.input_disabled_text,
            "readonlybackground": PALETTE.input_disabled_bg,
            "relief": "solid",
            "bd": CONTROL_BORDER_WIDTH,
            "highlightbackground": PALETTE.card_border,
            "highlightcolor": PALETTE.focus,
            "highlightthickness": RESTING_BORDER_THICKNESS,
        }
    return {
        "bg": PALETTE.input_disabled_bg,
        "fg": PALETTE.input_disabled_text,
        "disabledbackground": PALETTE.input_disabled_bg,
        "disabledforeground": PALETTE.input_disabled_text,
        "relief": "solid",
        "bd": CONTROL_BORDER_WIDTH,
        "highlightbackground": PALETTE.card_border,
        "highlightcolor": PALETTE.focus,
        "highlightthickness": RESTING_BORDER_THICKNESS,
    }


def selection_options(*, active: bool, enabled: bool = True) -> dict[str, object]:
    """Darstellung eines direkten Wahlschalters."""

    if not enabled:
        return {
            "bg": PALETTE.selection_disabled,
            "fg": PALETTE.input_disabled_text,
            "activebackground": PALETTE.selection_disabled,
            "activeforeground": PALETTE.input_disabled_text,
            "disabledforeground": PALETTE.input_disabled_text,
            "relief": "solid",
            "bd": CONTROL_BORDER_WIDTH,
            "cursor": "arrow",
            "highlightbackground": PALETTE.card_border,
            "highlightcolor": PALETTE.focus,
            "highlightthickness": RESTING_BORDER_THICKNESS,
        }
    return {
        "bg": PALETTE.selection if active else PALETTE.selection_inactive,
        "fg": "white" if active else PALETTE.text,
        "activebackground": PALETTE.selection_hover,
        "activeforeground": "white",
        "relief": "sunken" if active else "raised",
        "bd": CONTROL_BORDER_WIDTH,
        "cursor": "hand2",
        "highlightbackground": PALETTE.card_border,
        "highlightcolor": PALETTE.focus,
        "highlightthickness": RESTING_BORDER_THICKNESS,
    }


def action_options(*, critical: bool = False, enabled: bool = True) -> dict[str, object]:
    """Darstellung eines Aktionsbuttons."""

    if not enabled:
        return {
            "bg": PALETTE.disabled,
            "fg": PALETTE.disabled_text,
            "activebackground": PALETTE.disabled,
            "activeforeground": PALETTE.disabled_text,
            "disabledforeground": PALETTE.disabled_text,
            "relief": "raised",
            "bd": 2,
            "cursor": "arrow",
            "highlightbackground": PALETTE.card_border,
            "highlightcolor": PALETTE.focus,
            "highlightthickness": RESTING_BORDER_THICKNESS,
        }
    background = PALETTE.critical if critical else PALETTE.action
    hover = PALETTE.critical_hover if critical else PALETTE.action_hover
    return {
        "bg": background,
        "fg": "white",
        "activebackground": hover,
        "activeforeground": "white",
        "relief": "raised",
        "bd": 2,
        "cursor": "hand2",
        "highlightbackground": PALETTE.card_border,
        "highlightcolor": PALETTE.focus,
        "highlightthickness": RESTING_BORDER_THICKNESS,
    }


def information_options() -> dict[str, object]:
    """Darstellung einer reinen Informationsfläche."""

    return {
        "bg": PALETTE.information,
        "highlightbackground": PALETTE.card_border,
        "highlightthickness": RESTING_BORDER_THICKNESS,
        "bd": 0,
        "cursor": "arrow",
    }
