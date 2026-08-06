# CarenDMR 0.1.9.1.3 – RX-Initialisierung

## Ziel dieses Builds

Direkt nach einem vollständigen Programmneustart einen geführten Parrot-Test durchführen. Falls die erste Antwort wieder stumm bleibt, den kompletten `AudioTest_...`-Ordner bereitstellen. Entscheidend sind in `timeline.json` die Marker `RX_TRACE_DMRD`, `RX_TRACE_VERWORFEN`, `RX_TRACE_DECODE_OK` und `RX_TRACE_SUMME`.


## Ziel

Der erste Parrot-Test nach einem vollständigen Programmstart muss bereits beim ersten Versuch hörbar sein.

## Installation

```powershell
cd C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Die Dateien aus dem ZIP vollständig in den Projektordner übernehmen.

## Automatische Prüfung

```powershell
python -m pytest -q
python tools\release_check.py
```

## Verbindlicher Praxistest

1. CarenDMR vollständig beenden.
2. CarenDMR neu starten:

```powershell
python main.py --gui
```

3. Direkt nach dem Start den Audio-Assistenten oder „Parrot vorbereiten“ verwenden.
4. Prüfen: TG 9990, TS2, Privatruf.
5. Verbinden und genau einen Referenztext senden.
6. Die erste Parrot-Antwort muss vollständig hörbar sein; kein zweiter Versuch darf nötig sein.
7. Test anschließend nach einem weiteren vollständigen Programmneustart wiederholen.

## Git-Sicherung nach erfolgreichem Praxistest

```powershell
git status
git add .
git commit -m "Release 0.1.9.1.3 - RX-Initialisierung erster Parrot"
git tag -a v0.1.9.1.3 -m "CarenDMR 0.1.9.1.3"
git push origin feature/0.0.22-ui-redesign
git push origin v0.1.9.1.3
```
