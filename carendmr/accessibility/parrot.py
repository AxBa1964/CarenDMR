"""Local, non-sensitive announcements for a future locked Parrot test."""

from __future__ import annotations

from enum import Enum, auto

from .speech import SpeechOutput


class ParrotTestPhase(Enum):
    START = auto()
    TRANSMIT = auto()
    ECHO = auto()
    SUCCESS = auto()
    FAILURE = auto()
    TIMEOUT = auto()


_MESSAGES = {
    ParrotTestPhase.START: "Der sichere private Parrot-Test beginnt.",
    ParrotTestPhase.TRANSMIT: (
        "Stumme Testübertragung läuft. Es wird keine Sprache gesendet."
    ),
    ParrotTestPhase.ECHO: (
        "Die Übertragung ist beendet. Das Parrot-Echo wird jetzt empfangen."
    ),
    ParrotTestPhase.SUCCESS: "Der Parrot-Test wurde erfolgreich beendet.",
    ParrotTestPhase.FAILURE: (
        "Der Parrot-Test wurde sicher abgebrochen. Es erfolgt keine Wiederholung."
    ),
    ParrotTestPhase.TIMEOUT: (
        "Das Parrot-Echo wurde nicht innerhalb des Zeitlimits empfangen."
    ),
}


class ParrotTestAnnouncer:
    """Optional local speech output; carries no routing or test controls."""

    def __init__(self, output: SpeechOutput, *, enabled: bool = True) -> None:
        self._output = output
        self._enabled = enabled

    def announce(self, phase: ParrotTestPhase) -> None:
        if not isinstance(phase, ParrotTestPhase):
            raise TypeError("Die Parrot-Testphase ist ungültig.")
        if self._enabled:
            self._output.speak(_MESSAGES[phase])
