# Release 0.0.2

## Ziel

Reproduzierbare Release-Pakete erzeugen, ohne ZIP-Dateien oder andere
Build-Artefakte im Git-Repository zu speichern.

## Enthalten

- `tools/create_release_zip.py`
- automatische Ermittlung der Versionsnummer
- Prüfung der Pflichtdateien
- Ausschluss von Logs, Git-Daten, Caches und vorhandenen ZIP-Dateien
- Ausgabe nach `release/CarenDMR_<Version>.zip`
- automatische Tests für das Release-Werkzeug

## Noch nicht enthalten

- Mikrofon- und Lautsprechererkennung
- Audio-Test
- TTS
- PTT
- BrandMeister
- DMR-Audio
- USB-Bedieneinheit
