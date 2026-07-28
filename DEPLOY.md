# DEPLOY – CarenDMR 0.0.5.1

Alle Schritte in dieser Reihenfolge ausführen.

Projektpfad:

```text
C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
```

## 1. Projekt öffnen und Ausgangszustand prüfen

```powershell
cd C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
git status
```

Vor dem Update muss erscheinen:

```text
nothing to commit, working tree clean
```

Falls 0.0.5 noch nicht committed wurde, zuerst den dortigen Arbeitsstand
abschließen.

## 2. Update einspielen

`CarenDMR_0.0.5.1_Update.zip` entpacken und den Inhalt direkt über das
vorhandene Projekt kopieren. Vorhandene Dateien ersetzen.

## 3. Änderungen kontrollieren

```powershell
git status
```

Erwartete geänderte beziehungsweise neue Dateien:

```text
carendmr\version.py
tools\audio_check.py
tests\test_audio_check_entrypoint.py
CHANGELOG.md
RELEASE_INFO.md
DEPLOY.md
```

## 4. Alle Tests ausführen

```powershell
python -m unittest discover -s tests -v
```

Alle Tests müssen mit `OK` enden.

## 5. Direkten Skriptstart prüfen

```powershell
python tools\audio_check.py --help
```

Der Befehl muss die Hilfe anzeigen. Diese Fehlermeldung darf nicht mehr
auftreten:

```text
ModuleNotFoundError: No module named 'carendmr'
```

## 6. Modulstart zusätzlich prüfen

```powershell
python -m tools.audio_check --help
```

Auch dieser Befehl muss weiterhin funktionieren.

## 7. Audio-Diagnose direkt starten

```powershell
python tools\audio_check.py --diagnose-only
```

Bei Mikrofon und Wiedergabegerät jeweils Enter drücken, um die bereits
gespeicherten Geräte zu verwenden.

Erwartetes Ende:

```text
Audio-Diagnose abgeschlossen.
```

## 8. Versionsstart prüfen

```powershell
python main.py
```

Die Anwendung muss Version `0.0.5.1` melden. Danach regulär beenden.

## 9. Release-ZIP erzeugen

```powershell
python tools\create_release_zip.py
```

Erwartet:

```text
release\CarenDMR_0.0.5.1.zip
```

## 10. Änderungen vormerken

```powershell
git add .
git status
```

Kontrollieren:

- die sechs Update-Dateien sind vorgemerkt
- `config/audio.local.json` ist nicht enthalten
- Release-ZIP und Logs sind nicht enthalten

## 11. Commit erstellen

```powershell
git commit -m "CarenDMR 0.0.5.1 Audio-Startfehler behoben"
```

## 12. Abschluss prüfen

```powershell
git status
```

Erwartet:

```text
nothing to commit, working tree clean
```

## Ergebnis

0.0.5.1 ist abgeschlossen, wenn beide Startvarianten funktionieren, alle Tests
erfolgreich sind und der Arbeitsbaum nach dem Commit sauber ist.
