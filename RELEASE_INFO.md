# Release-Information – CarenDMR 0.0.7.1

## Ziel

0.0.7.1 korrigiert die bytegenaue Formatierung von Breiten- und Längengrad im RPTC-Stationsdatenpaket.

## Erfolgsfall

Das Werkzeug meldet:

```text
OK: BrandMeister-Anmeldung erfolgreich.
OK: MSTPONG empfangen.
UDP-Kanal geschlossen.
```

## Fehlerfälle

Verständliche Meldungen werden ausgegeben bei:

- DNS-Fehler
- UDP-Timeout
- `MSTNAK`
- unerwarteter Antwort
- falscher oder unvollständiger Konfiguration

## Nicht enthalten

- dauerhaft verbundener Client
- automatischer Wiederverbindungsversuch
- DMRD-Daten
- AMBE-/Vocoder-Verarbeitung
- Sprachempfang oder Sprachsendung

## Fehlerkorrektur 0.0.7.1

Version 0.0.7 verwendete vier Nachkommastellen. DroidStar verwendet sechs Nachkommastellen und übernimmt anschließend exakt 8 beziehungsweise 9 Bytes. Die abweichenden Felder führten zu `MSTNAK`.
