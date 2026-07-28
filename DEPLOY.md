# CarenDMR 0.0.1 – Installation und Prüfung unter Windows

Projektpfad:

```text
C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
```

## 1. ZIP-Datei entpacken

Den Inhalt der ZIP-Datei nach folgendem Ordner entpacken:

```text
C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
```

Dabei muss `main.py` direkt in diesem Ordner liegen.

## 2. VS Code öffnen

In PowerShell:

```powershell
cd C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
code .
```

## 3. Python-Version prüfen

```powershell
python --version
```

Empfohlen ist Python 3.12 oder neuer.

## 4. Tests ausführen

```powershell
python -m unittest discover -s tests -v
```

Erwartetes Ergebnis:

```text
Ran 3 tests
OK
```

## 5. CarenDMR starten

```powershell
python main.py
```

Erwartete Kernausgabe:

```text
CarenDMR
Version             : 0.0.1
Standard-Talkgroup  : 91
Status              : Grundsystem bereit
```

## 6. Logdatei prüfen

Nach dem ersten Start muss folgende Datei vorhanden sein:

```text
logs\carendmr.log
```

Die Datei muss unter anderem die Meldung enthalten:

```text
CarenDMR Grundsystem ist bereit
```

## 7. Git-Projekt anlegen

```powershell
git init
git add .
git commit -m "CarenDMR 0.0.1 Projektgrundgerüst"
```

Ein GitHub-Repository ist für die lokale Prüfung noch nicht erforderlich.
