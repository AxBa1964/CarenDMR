# CarenDMR 0.2.0 – Eigene Modulation vergleichen

## Ziel

Die eigene Aussendung wird nach dem lokalen AMBE-Loopback mit der aktiven Audio-Referenz verglichen. Rohmikrofon und empfangene DMR-Signale werden ausdrücklich nicht direkt miteinander verglichen.

## Installation

1. CarenDMR beenden.
2. Projekt sichern beziehungsweise Git-Status prüfen.
3. Die Dateien aus `CarenDMR_0.2.0.zip` in das Projektverzeichnis übernehmen. Lokale Zugangsdaten und produktive Konfigurationen nicht überschreiben.
4. Virtuelle Umgebung aktivieren:

```powershell
cd C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
.\.venv\Scripts\Activate.ps1
```

5. Abhängigkeiten prüfen:

```powershell
python -m pip install -r requirements.txt
```

6. Tests ausführen:

```powershell
python -m pytest -q
python tools\release_check.py
```

## Praxistest

1. CarenDMR mit `python main.py --gui` starten.
2. Im Reiter **Audio-Benchmark** prüfen, dass `TG91 Global` aktiv ist und gültige Referenzstationen vorhanden sind.
3. **Eigene Modulation testen** drücken.
4. Den eingeblendeten festen Referenztext geöffnet lassen beziehungsweise vorher lesen.
5. Auf der Betriebsseite mit TG 9990, TS2, Privatruf verbinden.
6. TX drücken, Beep und TX-Beginn abwarten und den Referenztext gleichmäßig sprechen.
7. TX beenden und die vollständige Parrot-Antwort abwarten.
8. Zum Reiter **Audio-Benchmark** zurückkehren. Der Vergleich muss automatisch erscheinen.
9. Prüfen, dass Referenz, DO1DPL, Abweichung und Empfehlungen sichtbar sind.
10. Es dürfen noch keine Tuner-Werte automatisch verändert werden.

Die Vergleichsdaten liegen unter:

```text
data\audio_benchmarks\references\TG91_Global\comparisons\
data\audio_benchmarks\references\TG91_Global\latest_comparison.json
```

## Git-Sicherung

```powershell
git status
git add .
git commit -m "Release 0.2.0 - Own modulation reference comparison"
git tag -a v0.2.0 -m "CarenDMR 0.2.0"
git push origin feature/0.0.22-ui-redesign
git push origin v0.2.0
git status
```
