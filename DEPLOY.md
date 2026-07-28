# DEPLOY – CarenDMR 0.0.7.6

Alle Schritte in dieser Reihenfolge ausführen.

Projektpfad:

```text
C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
```

## 1. Aktuellen Stand sichern

```powershell
cd C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
git status
python -m unittest discover -s tests -v
git add .
git status
git commit -m "CarenDMR 0.0.7.5 BrandMeister Kennungstests"
git push
```

Falls `git status` schon einen sauberen Stand meldet, entfallen `git add` und der
Commit.

## 2. Update einspielen

`CarenDMR_0.0.7.6_Update.zip` direkt über das bestehende Projekt entpacken und
vorhandene Dateien ersetzen.

`config\brandmeister.local.json` ist nicht im ZIP enthalten und wird nicht
überschrieben.

## 3. Lokale BrandMeister-Kennung anpassen

```powershell
notepad config\brandmeister.local.json
```

Diese Werte eintragen:

```json
"description": "CarenDMR Digital Voice Client",
"software_id": "20260728_CarenDMR",
"package_id": "MMDVM_CarenDMR_PC"
```

Die vorhandenen Zugangsdaten, Koordinaten und die Frequenz unverändert lassen.
Datei speichern und schließen.

## 4. Tests ausführen

```powershell
python -m unittest discover -s tests -v
```

Alle Tests müssen mit `OK` enden.

## 5. Reale BrandMeister-Anmeldung prüfen

```powershell
python tools\brandmeister_check.py --login-only
```

Erwartet:

```text
RPTL -> RPTACK
RPTK -> RPTACK
RPTC -> RPTACK
OK: BrandMeister-Anmeldung erfolgreich.
```

## 6. Version prüfen

```powershell
python main.py
```

Die Anwendung muss Version `0.0.7.6` melden.

## 7. Änderungen committen

```powershell
git status
git add .
git status
git commit -m "CarenDMR 0.0.7.6 eigene BrandMeister Kennung"
git push
git status
```

`config\brandmeister.local.json`, Logs, Cache-Dateien und ZIP-Dateien dürfen nicht
im Commit erscheinen.
