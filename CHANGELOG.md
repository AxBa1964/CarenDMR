# Änderungsverlauf

## 0.0.4 – Core und technisches Design

- Technisches Design für Core, Accessibility, Audio, TTS, Konfiguration,
  Logging und Tests dokumentiert.
- Synchronen, typisierten EventBus eingeführt.
- Zentralen StatusManager mit klar definierten Anwendungszuständen eingeführt.
- Statusänderungen werden als Ereignisse veröffentlicht.
- Wiederholte identische Zustände werden zur Vermeidung unnötiger Ansagen
  unterdrückt.
- Accessibility-Schicht mit verständlichen deutschen Statusmeldungen ergänzt.
- Austauschbare SpeechOutput-Schnittstelle und Konsolenausgabe eingeführt.
- Automatisierte Tests für EventBus, StatusManager und Accessibility ergänzt.
- `sounddevice` als bevorzugte Grundlage für Version 0.0.5 festgehalten.
- Noch keine Audio-, TTS-, BrandMeister- oder DMR-Funktion implementiert.

## 0.0.3 – DroidStar-Architekturanalyse

- Architektur und relevante BrandMeister-/DMR-Abläufe dokumentiert.
- Grundlegende Projektentscheidungen festgehalten.

## 0.0.2 – Release-Werkzeug

- Plattformübergreifende Release-Erzeugung mit Python ergänzt.
- Release-Ausschlüsse und Tests ergänzt.

## 0.0.1 – Projektgrundgerüst

- Erstes Projektgrundgerüst erstellt.
