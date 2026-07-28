"""Erste Audio-Prüfungen für die wachsende Systemdiagnose."""

from __future__ import annotations

from carendmr.audio import AudioDirection, AudioManager

from .models import DiagnosticResult, DiagnosticStatus


class AudioDiagnostics:
    def __init__(self, manager: AudioManager) -> None:
        self.manager = manager

    def run(self) -> tuple[DiagnosticResult, ...]:
        try:
            self.manager.scan()
        except Exception as exc:
            return (
                DiagnosticResult(
                    check_id="audio_backend",
                    status=DiagnosticStatus.ERROR,
                    summary="Die Audio-Geräte konnten nicht abgefragt werden.",
                    action=str(exc),
                ),
            )

        results: list[DiagnosticResult] = []
        results.append(self._check_direction(AudioDirection.INPUT))
        results.append(self._check_direction(AudioDirection.OUTPUT))
        return tuple(results)

    def _check_direction(
        self,
        direction: AudioDirection,
    ) -> DiagnosticResult:
        devices = self.manager.list_devices(direction)
        if direction is AudioDirection.INPUT:
            check_id = "audio_input"
            noun = "Mikrofon"
        else:
            check_id = "audio_output"
            noun = "Wiedergabegerät"

        if not devices:
            return DiagnosticResult(
                check_id=check_id,
                status=DiagnosticStatus.ERROR,
                summary=f"Es wurde kein {noun} gefunden.",
                action=(
                    "Bitte schließen Sie ein geeignetes Gerät an und "
                    "starten Sie die Diagnose erneut."
                ),
            )

        try:
            resolved = self.manager.resolve(direction)
        except Exception as exc:
            return DiagnosticResult(
                check_id=check_id,
                status=DiagnosticStatus.ERROR,
                summary=f"Das {noun} konnte nicht ausgewählt werden.",
                action=str(exc),
            )

        status = (
            DiagnosticStatus.WARNING
            if resolved.used_fallback
            else DiagnosticStatus.OK
        )
        return DiagnosticResult(
            check_id=check_id,
            status=status,
            summary=resolved.message,
        )
