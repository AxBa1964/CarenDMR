# Änderungsverlauf

## 0.0.5.1 – Direkter Start des Audio-Werkzeugs

- `python tools\audio_check.py` funktioniert jetzt direkt aus dem
  Projektverzeichnis.
- Der Projektpfad wird vor dem Import des Pakets `carendmr` sauber ergänzt.
- Der weiterhin mögliche Modulstart
  `python -m tools.audio_check` bleibt unverändert erhalten.
- Regressionstest für den direkten Skriptstart ergänzt.
- Keine neue Audio-, Netzwerk-, BrandMeister- oder DMR-Funktion.

## 0.0.5 – Audiogeräte und lokale Diagnose

- Audio-Gerätemodell mit stabilerer Identität eingeführt.
- AudioBackend-Schnittstelle für hardwareunabhängige Tests ergänzt.
- sounddevice-Backend für Windows und macOS implementiert.
- Eingabe- und Wiedergabegeräte werden erkannt und getrennt aufgelistet.
- Betriebssystem-Standardgeräte werden markiert.
- Geräteauswahl wird ohne veränderliche PortAudio-Indizes gespeichert.
- Fehlende gespeicherte Geräte fallen verständlich auf ein Standardgerät
  zurück.
- Lokaler Aufnahme-/Wiedergabe-Selbsttest ergänzt.
- Interaktives Werkzeug `tools/audio_check.py` ergänzt.
- Erste AudioDiagnostics mit handlungsorientierten Ergebnissen ergänzt.
- Tests für Geräteerkennung, Auswahl, Speicherung, Rückfall, Selbsttest und
  Diagnose ergänzt.
- `sounddevice` und `numpy` als Audioabhängigkeiten aufgenommen.
- Noch keine BrandMeister-, DMR- oder Vocoder-Funktion.

## 0.0.4 – Core und technisches Design

- EventBus, StatusManager und Accessibility-Grundlage eingeführt.

## 0.0.3 – DroidStar-Architekturanalyse

- Architektur und relevante BrandMeister-/DMR-Abläufe dokumentiert.

## 0.0.2 – Release-Werkzeug

- Plattformübergreifende Release-Erzeugung mit Python ergänzt.

## 0.0.1 – Projektgrundgerüst

- Erstes Projektgrundgerüst erstellt.
