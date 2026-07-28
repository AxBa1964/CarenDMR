# CarenDMR

CarenDMR ist ein bewusst einfacher, barrierearmer DMR-Client für das
BrandMeister-Netzwerk. Das Programm wird zunächst für Caren entwickelt.

## Festes Projektziel

CarenDMR soll:

- sich mit BrandMeister verbinden,
- Talkgroup 91 hörbar empfangen,
- per gedrückter PTT verständlich auf Talkgroup 91 senden,
- vollständig per Tastatur und später per externer USB-Bedieneinheit
  bedienbar sein,
- wichtige Zustände akustisch melden,
- unter Windows und später unter macOS laufen.

CarenDMR ist kein allgemeines Digitalfunk-Framework. Andere Betriebsarten
wie D-Star, YSF, P25 oder NXDN gehören ausdrücklich nicht zum Projektumfang.

## Version 0.0.2

Diese Version ergänzt das Release-Werkzeug:

```text
python tools/create_release_zip.py
```

Das Werkzeug erzeugt:

```text
release/CarenDMR_0.0.2.zip
```

Git-Daten, Logs, Caches, virtuelle Umgebungen und bereits vorhandene
ZIP-Dateien werden nicht in das Release übernommen.

Eine BrandMeister-Verbindung ist noch nicht enthalten.
