# Release-Information – CarenDMR 0.0.7.2

## Ziel

Version 0.0.7.2 liefert eine vollständige, abschaltbare Paketdiagnose für den BrandMeister-Handshake. Damit lässt sich das von CarenDMR gesendete RPTC-Paket bytegenau mit einem funktionierenden DroidStar-Mitschnitt vergleichen.

## Nutzung

```powershell
python tools\brandmeister_check.py
```

Die Diagnose zeigt standardmäßig alle gesendeten und empfangenen Pakete mit Richtung, Paketname, Länge, Hexwerten und ASCII-Darstellung. Für die kompakte bisherige Ausgabe:

```powershell
python tools\brandmeister_check.py --no-packet-dump
```

## Sicherheit

Das Hotspot Security Password wird nicht ausgegeben. Alle Dateien mit dem Muster `config/*.local.json` sind von der Release-Erzeugung ausgeschlossen.

## Nicht enthalten

- Änderung der RPTC-Feldwerte
- ESSID-Unterstützung
- DMRD-Sprachdatenverarbeitung
- automatischer Wiederverbindungsversuch
