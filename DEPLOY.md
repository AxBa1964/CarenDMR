# CarenDMR 0.0.3 – Aktualisierung und Prüfung unter Windows

Projektpfad:

```text
C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
```

## 1. In das Projekt wechseln

```powershell
cd C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
```

## 2. Aktuellen Git-Stand prüfen

```powershell
git status
git log --oneline -3
```

Version 0.0.2 muss committed sein und der Arbeitsbaum sollte sauber sein.

## 3. Update übernehmen

Den Inhalt des Update-Pakets über den vorhandenen Projektordner kopieren.
Vorhandene Dateien ersetzen.

## 4. Tests ausführen

```powershell
python -m unittest discover -s tests -v
```

Erwartetes Ergebnis:

```text
Ran 8 tests
OK
```

## 5. Anwendung starten

```powershell
python main.py
```

Erwartete Kernausgabe:

```text
Version             : 0.0.3
Standard-Talkgroup  : 91
Status              : Grundsystem bereit
```

## 6. Neue Dokumente prüfen

```powershell
notepad docs\ARCHITECTURE.md
notepad docs\DECISIONS.md
```

Beide Dateien müssen vorhanden und lesbar sein.

## 7. Release-ZIP erzeugen

```powershell
python tools\create_release_zip.py
```

Erwartete Datei:

```text
release\CarenDMR_0.0.3.zip
```

## 8. Git-Status prüfen

```powershell
git status
```

Die Datei unter `release` darf nicht angezeigt werden.

## 9. Version committen

```powershell
git add .
git commit -m "CarenDMR 0.0.3 DroidStar Architektur-Analyse"
```

## 10. Abschlussprüfung

```powershell
git status
git log --oneline -3
```

Erwartet wird ein sauberer Arbeitsbaum.
