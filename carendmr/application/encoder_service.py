"""Anwendungsschicht für Auswahl und Offline-Prüfung optionaler Encoder."""

from __future__ import annotations

from pathlib import Path

from carendmr.encoder import EncoderDiagnostics, EncoderSettingsStore, verify_plugin


class EncoderService:
    """Kennt Plugin-Konfiguration, aber keinerlei DMRD- oder Sendefunktion."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root)
        self.settings = EncoderSettingsStore(
            self.project_root / "config" / "encoder.local.json"
        )

    @property
    def configured_plugin_path(self) -> Path | None:
        return self.settings.load_plugin_path()

    def configure_and_verify(self, plugin_path: Path) -> EncoderDiagnostics:
        diagnostics = verify_plugin(self.project_root, plugin_path)
        self.settings.save_plugin_path(plugin_path)
        return diagnostics

    def verify_configured(self) -> EncoderDiagnostics:
        plugin_path = self.configured_plugin_path
        if plugin_path is None:
            raise RuntimeError("Es ist noch kein DroidStar-Vocoder-Plugin ausgewählt.")
        return verify_plugin(self.project_root, plugin_path)
