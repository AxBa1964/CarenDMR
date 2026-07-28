# Release-Information – CarenDMR 0.0.4

## Ziel

Version 0.0.4 schafft die erste ausführbare Architekturgrundlage für alle
späteren Komponenten. Sie verbindet noch kein Funknetz und greift noch nicht
auf Audiohardware zu.

## Enthalten

- `carendmr/core/events.py`
- `carendmr/core/status.py`
- `carendmr/accessibility/messages.py`
- `carendmr/accessibility/speech.py`
- `docs/TECHNICAL_DESIGN.md`
- erweiterte `docs/DECISIONS.md`
- neue automatisierte Tests

## Abnahmekriterien

- Alle bisherigen und neuen Tests laufen erfolgreich.
- `python main.py` startet weiterhin wie zuvor.
- EventBus verteilt Ereignisse genau einmal je Registrierung.
- StatusManager veröffentlicht nur echte Änderungen.
- Statusänderungen können unabhängig von echter TTS verständlich ausgegeben
  werden.
- Es wird keine neue externe Python-Abhängigkeit benötigt.
- Nach dem Commit ist der Git-Arbeitsbaum sauber.

## Bewusst nicht enthalten

- Audio-Gerätesuche
- Audio-Selbsttest
- echte Sprachausgabe
- BrandMeister-Verbindung
- DMR-Pakete
- Vocoder
