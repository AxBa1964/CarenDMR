"""Funkfachliche Formatierung für Screenreader-Kontexte."""
from __future__ import annotations


class RadioAccessibilityFormatter:
    @staticmethod
    def digits(value: object) -> str:
        return " ".join(character for character in str(value) if character.isdigit())

    @staticmethod
    def call_type(call_type: str) -> str:
        return "Privatruf" if str(call_type).lower() == "private" else "Gruppenruf"

    def operation_context(self, talkgroup: int, timeslot: int, call_type: str, state_label: str) -> str:
        return (
            f"Betrieb. Talkgroup {talkgroup}. "
            f"Timeslot {timeslot}. Rufart {self.call_type(call_type)}. {state_label}."
        )

    def pending_talkgroup(self, value: str) -> str:
        return f"Neue Talkgroup {self.digits(value)}."

    @staticmethod
    def history_context(count: int) -> str:
        return f"QSO-Historie. {count} Station" + ("." if count == 1 else "en.")
