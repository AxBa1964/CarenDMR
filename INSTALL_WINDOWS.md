# Installation unter Windows

Getestete Grundlage: Windows 11, Python 3.12 und MSYS2 UCRT64.

## 1. Voraussetzungen

- Git für Windows
- Python 3.12 oder neuer von python.org
- „Python zu PATH hinzufügen“ bei der Installation aktivieren
- MSYS2 mit MinGW-w64 für den nativen Empfangsdecoder

MSYS2 installieren:

```powershell
winget install --id MSYS2.MSYS2 -e
```

Danach einmal **MSYS2 UCRT64** aus dem Startmenü öffnen und ausführen:

```bash
pacman -Syu
pacman -S --needed mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-binutils
```

Falls `pacman -Syu` zum Schließen des Fensters auffordert, das UCRT64-Fenster
erneut öffnen und beide Befehle vollständig abschließen.

## 2. Repository klonen

```powershell
New-Item -ItemType Directory -Force C:\Users\abaru\OneDrive\AB_Entwicklung
Set-Location C:\Users\abaru\OneDrive\AB_Entwicklung
git clone https://github.com/AxBa1964/CarenDMR.git
Set-Location CarenDMR
```

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

## 4. Nativen Empfangsdecoder bauen

Im Projektverzeichnis:

```powershell
powershell -ExecutionPolicy Bypass -File .\native\build_windows.ps1
```

Bei Erfolg entsteht lokal:

```text
native\carendmr_mbe.dll
```

Die DLL wird geprüft und nicht in Git oder das Release-ZIP aufgenommen. Sie
exportiert ausschließlich die drei Empfangsfunktionen; ein Encoder ist nicht
enthalten.

## 5. Tests

```powershell
python -m unittest discover -s tests -v
python main.py
```

## 6. TG91-Live-Empfang

Voraussetzung ist `config\brandmeister.local.json`.

```powershell
python main.py --listen
```

Der Lauf ist auf TG91, Timeslot 2 und maximal 60 Sekunden begrenzt. Er sendet
keine DMRD-Pakete.

## Aktualisieren

```powershell
git status
git pull --ff-only
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File .\native\build_windows.ps1
python -m unittest discover -s tests -v
```

`git pull` nur bei sauberem Arbeitsbaum ausführen.
