CarenDMR 0.2.1.73 – Delta auf 0.2.1.72

Enthalten:
- TX-Zeitbegrenzung in Einstellungen: 0 = unbegrenzt, bis 300 Sekunden
- optische + akustische Warnung in den letzten 10 Sekunden
- manueller QSO-Mitschnitt als WAV aus digitalem TX/RX-PCM
- Mitschnitt endet automatisch bei Zielwechsel oder Trennen
- Dateiname Mitschnitt_YYYY-MM-DD_HH-MM-SS.wav im Ordner Mitschnitte
- QSO-Historie: gesprochene Stationen hellgrün
- aktuelle Station: kompakte QSO-Zeile mit letztem QSO und Markieren-Button
- letzte drei Stationen: zusätzliche Spalte Letztes QSO
- manuelles QSO-Markieren auch beim ersten laufenden Kontakt
- Version 0.2.1.73

Installation:
Delta-ZIP direkt über einen vollständigen CarenDMR-0.2.1.72-Projektstand
entpacken und vorhandene Dateien ersetzen.

Gezielter Test:
  python -m pytest .\tests\test_release_02173.py -q
