"""Gemeinsame Datenmodelle für Diagnoseprüfungen."""

from dataclasses import dataclass
from enum import Enum


class DiagnosticStatus(str, Enum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class DiagnosticResult:
    check_id: str
    status: DiagnosticStatus
    summary: str
    action: str | None = None

    def spoken_text(self) -> str:
        if self.action:
            return f"{self.summary} {self.action}".strip()
        return self.summary
