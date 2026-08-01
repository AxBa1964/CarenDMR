# Deployment CarenDMR 0.0.18.3

Dieses Dokument ist die verbindliche chronologische Anleitung für Version 0.0.18.3.
Lokale Zugangsdaten und produktive Datenbanken dürfen dabei nicht überschrieben
oder committed werden.

## 1. Projektstand prüfen

```powershell
cd C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
git status
git branch --show-current
git pull --ff-only
```

## 2. Dateien unter Windows entsperren

```powershell
Get-ChildItem -Recurse -File | Unblock-File
```

## 3. Virtuelle Umgebung aktivieren

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## 4. Nativen Empfangsdecoder bauen

```powershell
.\native\build_windows.ps1
```

## 5. Vollständige Tests ausführen

```powershell
python -m unittest discover -s tests -v
```

Erwartet werden 168 erfolgreiche Tests und `OK`.

## 6. Anwendung starten

```powershell
python main.py --gui
```

## 7. Empfang praktisch prüfen

- Mit „Verbinden und empfangen“ verbinden.
- TG91-Empfang bleibt ohne feste Zeitgrenze aktiv.
- Aktuelle Station und QSO-Historie werden aktualisiert.
- „Trennen“ beendet Empfang und Audio sauber.

## 8. Lokalen Audio-Sendepfad prüfen

Im Reiter **„Senden – lokaler Audiotest“**:

1. Mikrofon auswählen oder Standardmikrofon übernehmen.
2. „5 Sekunden Testaufnahme“ ausführen.
3. Prüfen, ob sich die Pegelanzeige bewegt.
4. „Testaufnahme wiedergeben“ ausführen und Sprache beurteilen.
5. Ausgabelautstärke zwischen 0 und 400 Prozent prüfen.
6. AGC ein- und ausschalten und verschiedene Gegenstationen vergleichen.
7. Während „Testaufnahme wiedergeben“ prüfen, dass DMR-Audio lokal stumm bleibt.
8. Optional „4 Sekunden Loopback“ ausführen.

Version 0.0.18.3 sendet dabei keine DMRD-Pakete. Es gibt keine PTT und keinen
AMBE-Encoder.

## 9. Release-ZIP erzeugen

```powershell
python tools\create_release_zip.py
```

Das ZIP darf insbesondere nicht enthalten:

- `.git`, `.venv` oder Cache-Verzeichnisse,
- `config\*.local.json`,
- `data\contacts.db` oder `data\qso_history.db`,
- Audioaufnahmen, Logs oder Paketmitschnitte,
- `*.dll`, `*.so` oder `*.dylib`.

## 10. Git prüfen, committen und pushen

```powershell
git status
git diff --check
git diff
git add <gezielte Dateien>
git status
git diff --cached --check
git diff --cached
git commit -m "CarenDMR 0.0.18.3 Audiopegel und samplegenaue Aufnahme"
git push -u origin <branch>
```
