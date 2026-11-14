CarenDMR 0.2.1.82 – Delta
==========================

Neu: QSO-Synchronisation zwischen mehreren Rechnern.

Prinzip:
- Jeder Rechner behält seine eigene lokale data/qso_history.db.
- In einem frei wählbaren gemeinsamen Ordner (z. B. OneDrive/Dropbox/iCloud Drive)
  schreibt jeder Rechner eine eigene atomare JSON-Snapshot-Datei.
- Beim Start, bei Änderungen und über den neuen Button "Synchronisieren" werden
  fremde Snapshots zusammengeführt und anschließend der lokale Gesamtstand veröffentlicht.
- Dadurch wird keine geöffnete SQLite-Datei zwischen Rechnern geteilt.

Synchronisiert werden:
- QSO-/Empfangshistorie
- Status "Gesprochen" / "Nur gehört", einschließlich Rücknahme
- Zeitpunkt der QSO-Bestätigung
- QRZ.com LOGID / bereits geloggter Status

Konfiguration:
Einstellungen -> Datenbanken -> QSO-Synchronisation zwischen Rechnern
1. Aktivieren
2. Auf beiden Rechnern denselben Cloud-Ordner auswählen
3. Übernehmen

Lokale Dateien:
- config/qso_sync.local.json: lokaler Sync-Pfad (durch .gitignore ausgeschlossen)
- config/qso_sync_device.local.json: eindeutige Gerätekennung (durch .gitignore ausgeschlossen)

Wichtig:
Die beiden Rechner dürfen unterschiedliche lokale Projekt- und Datenbankpfade haben.
Die Sync-Snapshots sind pro Gerät getrennt, um Cloud-Dateikonflikte zu vermeiden.
