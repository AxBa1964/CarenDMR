# Installation unter Windows

Getestete Grundlage: Windows 11 und Python 3.12.

## 1. Voraussetzungen

- Git für Windows
- Python 3.12 oder neuer von python.org
- „Python zu PATH hinzufügen“ bei der Installation aktivieren
- für den nativen Decoder eine C-Toolchain; bis deren Windows-Build
  dokumentiert ist, bleiben die nativen Decoderprüfungen macOS/Linux-fokussiert

## 2. Repository klonen

```powershell
New-Item -ItemType Directory -Force C:\Users\abaru\OneDrive\AB_Entwicklung
Set-Location C:\Users\abaru\OneDrive\AB_Entwicklung
git clone https://github.com/AxBa1964/CarenDMR.git
Set-Location CarenDMR
```

Den Basisordner bei einem anderen Windows-Benutzer entsprechend anpassen.

## 3. Python-Umgebung

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Falls PowerShell die Aktivierung blockiert:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
```

Die Änderung gilt nur für das aktuelle Fenster.

## 4. Tests

```powershell
python -m unittest discover -s tests -v
python main.py
```

Für Audiozugriff muss Windows Desktop-Apps den Mikrofonzugriff erlauben.

## Aktualisieren

```powershell
git status
git pull --ff-only
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

`git pull` nur bei sauberem Arbeitsbaum ausführen.
