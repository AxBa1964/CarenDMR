# DEPLOY – CarenDMR 0.0.7.1

Alle Schritte in dieser Reihenfolge ausführen.

Projektpfad:

```text
C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
```

## 1. Ausgangszustand prüfen

```powershell
cd C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
git status
```

Erwartet:

```text
nothing to commit, working tree clean
```

## 2. Update einspielen

`CarenDMR_0.0.7.1_Update.zip` entpacken und den Inhalt direkt über das bestehende
Projekt kopieren. Vorhandene Dateien ersetzen.

Die lokale Datei `config\\brandmeister.local.json` bleibt dabei unverändert.

## 3. Lokale Konfiguration von Git ausschließen

`.gitignore` öffnen:

```powershell
notepad .gitignore
```

Diese Zeile ergänzen, falls sie fehlt:

```text
config/brandmeister.local.json
```

Speichern und schließen.

## 4. Änderungen prüfen

```powershell
git status
```

Die neue lokale Konfiguration darf später nicht in Git erscheinen.

## 5. Alle Tests ausführen

```powershell
python -m unittest discover -s tests -v
```

Alle Tests müssen mit `OK` enden.

## 6. BrandMeister-Konfiguration erzeugen

```powershell
Copy-Item config\brandmeister.example.json config\brandmeister.local.json
notepad config\brandmeister.local.json
```

Folgende Werte eintragen:

- `host`: der von Dir verwendete BrandMeister-Master
- `port`: normalerweise `62031`
- `dmr_id`: Deine persönliche numerische DMR-ID
- `password`: das in BrandMeister SelfCare gesetzte **Hotspot Security Password**
- `callsign`: Dein Rufzeichen, bei Dir `DO1DPL`

Breiten-/Längengrad, Ort und URL dürfen für den ersten Test leer beziehungsweise
null bleiben.

Wichtig: Nicht das normale BrandMeister-Webkennwort verwenden.

Speichern und Editor schließen.

## 7. Git-Ausschluss kontrollieren

```powershell
git status
```

`config/brandmeister.local.json` darf nicht angezeigt werden.

## 8. Einmaligen Login-Test starten

```powershell
python tools\brandmeister_check.py
```

Das Werkzeug:

1. meldet sich an,
2. prüft `RPTPING`/`MSTPONG`,
3. sendet `RPTCL`,
4. schließt den UDP-Kanal.

Es sendet noch keine Sprache und keine DMRD-Funkdaten.

## 9. Bei Timeout ohne Ping erneut nur den Login prüfen

Nur falls die Anmeldung erfolgreich gemeldet wird, aber die Ping-Prüfung
scheitert:

```powershell
python tools\brandmeister_check.py --login-only
```

Die vollständige Ausgabe für die Fehleranalyse aufbewahren.

## 10. Versionsstart prüfen

```powershell
python main.py
```

Die Anwendung muss Version `0.0.7.1` melden. Danach regulär beenden.

## 11. Release-ZIP erzeugen

```powershell
python tools\create_release_zip.py
```

Erwartet:

```text
release\CarenDMR_0.0.7.1.zip
```

## 12. Änderungen vormerken

```powershell
git add .
git status
```

Kontrollieren:

- BrandMeister-Module sind enthalten
- Tests und Dokumentation sind enthalten
- `config/brandmeister.local.json` ist nicht enthalten
- Release-ZIP und Logs sind nicht enthalten

## 13. Commit erstellen

```powershell
git commit -m "CarenDMR 0.0.7.1 BrandMeister Login"
```

## 14. Abschluss prüfen

```powershell
git status
```

Erwartet:

```text
nothing to commit, working tree clean
```

## Ergebnis

0.0.7 ist abgeschlossen, wenn alle Tests erfolgreich sind und der reale
Login-Test entweder erfolgreich endet oder eine eindeutig auswertbare
BrandMeister-Fehlermeldung liefert.
