CarenDMR 0.2.1.76 – QRZ.com Logbook

- manueller Upload ausdrücklich bestätigter QSOs zu QRZ.com
- QRZ ACTION=INSERT ohne OPTION=REPLACE
- 70cm / DMR; keine erfundene Frequenz
- UTC-Datum und UTC-Zeit aus dem lokalen QSO-Zeitstempel
- TG/TS als ADIF-Kommentar
- Bestätigungsdialog vor jedem Upload
- QRZ LOGID wird lokal in data/qso_history.db gespeichert
- lokale Dublettensperre für dasselbe markierte QSO
- API Access Key unter Einstellungen > Datenbanken > QRZ.com Logbook
- Key ausschließlich in config/qrz_logbook.local.json; durch *.local.json von Git ausgeschlossen
- User-Agent CarenDMR/0.2.1.76
- bestehender Rekursionsfehler bei leerer aktueller QSO-Anzeige korrigiert

Test:
  python -m pytest .\tests\test_qrz_logbook_02176.py -q
Erwartung: 8 passed
