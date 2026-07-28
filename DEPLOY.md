# CarenDMR 0.0.2 – Aktualisierung und Prüfung unter Windows

Projektpfad:

```text
C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
```

## 1. Sicherheitsprüfung des aktuellen Git-Standes

```powershell
cd C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
git status
```

Der bisherige Stand 0.0.1 muss bereits committed sein.

## 2. ZIP-Datei aus Git entfernen

Dieser Schritt ist nur erforderlich, wenn `CarenDMR_0.0.1.zip` noch von Git
verwaltet wird:

```powershell
git rm --cached CarenDMR_0.0.1.zip
```

Die lokale ZIP-Datei kann danach gelöscht werden. Künftige ZIP-Dateien werden
durch `.gitignore` automatisch ignoriert.

## 3. Dateien aus Version 0.0.2 übernehmen

Den Inhalt des bereitgestellten Pakets über den vorhandenen Projektordner
kopieren. Vorhandene Dateien ersetzen.

`main.py` muss weiterhin direkt in diesem Ordner liegen:

```text
C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
```

## 4. Python-Version prüfen

```powershell
python --version
```

Erwartet wird Python 3.12 oder neuer.

## 5. Alle Tests ausführen

```powershell
python -m unittest discover -s tests -v
```

Erwartetes Ergebnis:

```text
Ran 8 tests
OK
```

## 6. CarenDMR starten

```powershell
python main.py
```

Erwartete Kernausgabe:

```text
CarenDMR
Version             : 0.0.2
Standard-Talkgroup  : 91
Status              : Grundsystem bereit
```

## 7. Release-ZIP erzeugen

```powershell
python tools\create_release_zip.py
```

Erwartete Ausgabe beginnt mit:

```text
Release erstellt
----------------------------------------
Version : 0.0.2
```

Die erzeugte Datei befindet sich hier:

```text
release\CarenDMR_0.0.2.zip
```

## 8. Inhalt der ZIP-Datei prüfen

Die ZIP-Datei darf insbesondere nicht enthalten:

```text
.git
logs
release
__pycache__
.venv
CarenDMR_0.0.1.zip
```

Sie muss mindestens enthalten:

```text
main.py
README.md
DEPLOY.md
CHANGELOG.md
RELEASE_INFO.md
carendmr\version.py
config\config.json
tools\create_release_zip.py
```

## 9. Git-Status prüfen

```powershell
git status
```

Die erzeugte ZIP-Datei unter `release` darf nicht als unversionierte Datei
angezeigt werden.

## 10. Version 0.0.2 committen

```powershell
git add .
git commit -m "CarenDMR 0.0.2 Release-Werkzeug"
```

## 11. Abschlussprüfung

```powershell
git status
git log --oneline -3
```

Erwartet wird ein sauberer Arbeitsbaum.
