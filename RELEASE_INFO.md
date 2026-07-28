# Release-Information – CarenDMR 0.0.5.1

## Ziel

Version 0.0.5.1 behebt ausschließlich den fehlerhaften direkten Start des
Audio-Werkzeugs.

## Behobener Fehler

Dieser Befehl aus `DEPLOY.md` schlug in 0.0.5 fehl:

```powershell
python tools\audio_check.py --diagnose-only
```

Fehlermeldung:

```text
ModuleNotFoundError: No module named 'carendmr'
```

Das Werkzeug ergänzt nun vor dem Paketimport automatisch das
Projektverzeichnis im Python-Suchpfad.

## Abnahmekriterien

Beide Startvarianten funktionieren:

```powershell
python tools\audio_check.py --help
python -m tools.audio_check --help
```

Danach funktionieren auch:

```powershell
python tools\audio_check.py --diagnose-only
python tools\audio_check.py
```

Alle automatisierten Tests enden mit `OK`.

## Bewusst nicht enthalten

- keine Änderung der Geräteauswahl
- keine Änderung des Aufnahme-/Wiedergabeablaufs
- kein Netzwerk
- kein BrandMeister
- kein DMR
- kein Vocoder
