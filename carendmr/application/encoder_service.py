"""Anwendungsschicht für Auswahl und Offline-Prüfung optionaler Encoder."""

from __future__ import annotations

from pathlib import Path

from carendmr.encoder import EncoderDiagnostics, EncoderSettingsStore, verify_plugin
from carendmr.encoder.md380_dynarmic import Md380DynarmicEncoder


class EncoderService:
    """Kennt Plugin-Konfiguration, aber keinerlei DMRD- oder Sendefunktion."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root)
        self.settings = EncoderSettingsStore(
            self.project_root / "config" / "encoder.local.json"
        )


    @property
    def md380_bridge_path(self) -> Path:
        from carendmr.encoder.md380_dynarmic import default_md380_bridge_path
        return default_md380_bridge_path(self.project_root)

    @property
    def md380_available(self) -> bool:
        return self.md380_bridge_path.is_file()

    def create_transmit_encoder(self):
        """Erzeugt den bevorzugten Live-TX-Encoder.

        MD380/DroidStar ist nach dem kontrollierten A/B-Hörtest der Standard.
        Das bisherige Plugin bleibt ausschließlich als Fallback erhalten, falls
        die native MD380-Bridge auf einer Installation noch nicht gebaut ist.
        """
        if self.md380_available:
            return Md380DynarmicEncoder(self.project_root, input_gain_db=0.0)
        plugin_path = self.detect_plugin()
        if plugin_path is None:
            raise RuntimeError(
                "Weder MD380-Dynarmic-Bridge noch ein bisheriges Vocoder-Plugin ist verfügbar."
            )
        from carendmr.encoder import DroidStarPluginEncoder
        return DroidStarPluginEncoder(self.project_root, plugin_path)

    @property
    def configured_plugin_path(self) -> Path | None:
        return self.settings.load_plugin_path()


    def discover_plugin_candidates(self) -> tuple[Path, ...]:
        """Findet bekannte Vocoder-Plugins unabhängig von einer Dateiendung."""
        search_roots = (
            self.project_root / "plugins",
            self.project_root / "plugin",
            self.project_root,
        )
        candidates: list[Path] = []
        seen: set[Path] = set()
        for directory in search_roots:
            if not directory.is_dir():
                continue
            for pattern in ("vocoder_plugin*", "*vocoder*.dll", "*vocoder*.so", "*vocoder*.dylib"):
                for path in directory.glob(pattern):
                    if not path.is_file():
                        continue
                    resolved = path.resolve()
                    if resolved in seen:
                        continue
                    seen.add(resolved)
                    candidates.append(path)
        return tuple(sorted(candidates, key=lambda item: str(item).lower()))

    def detect_plugin(self) -> Path | None:
        """Liefert das konfigurierte oder ein eindeutig erkanntes Plugin."""
        configured = self.configured_plugin_path
        if configured is not None and configured.is_file():
            return configured
        candidates = self.discover_plugin_candidates()
        if len(candidates) == 1:
            return candidates[0]
        preferred = [path for path in candidates if path.name == "vocoder_plugin.winnt.x86_64"]
        return preferred[0] if len(preferred) == 1 else None

    def configure_and_verify(self, plugin_path: Path) -> EncoderDiagnostics:
        diagnostics = verify_plugin(self.project_root, plugin_path)
        self.settings.save_plugin_path(plugin_path)
        return diagnostics

    def verify_configured(self) -> EncoderDiagnostics:
        if self.md380_available:
            encoder = self.create_transmit_encoder()
            try:
                encoder.encode_2450x1150((0,) * 160)
            finally:
                close = getattr(encoder, "close", None)
                if close is not None:
                    close()
            return EncoderDiagnostics(
                backend="MD380/Dynarmic",
                plugin_path=str(self.md380_bridge_path),
                ready=True,
                encoded_bytes=9,
                message=f"Native TX-Bridge bereit: {self.md380_bridge_path}",
            )

        plugin_path = self.configured_plugin_path
        if plugin_path is None:
            raise RuntimeError(
                "Weder MD380-Dynarmic-Bridge noch ein DroidStar-Vocoder-Plugin ist verfügbar."
            )
        return verify_plugin(self.project_root, plugin_path)
