# Entwicklung: CarenDMR aus dem Quellcode starten (Windows)

Stand 0.2.1.91. Ersetzt die früheren `INSTALL_*.md`. Anwender nehmen den
Installer; diese Anleitung ist für die Arbeit am Code.

## Voraussetzungen

- Windows 11, Git für Windows
- Python 3.12 (bei der Installation „Python zu PATH hinzufügen“)
- MSYS2 UCRT64 – nur nötig, um die MD380-Bridge oder ein Setup zu bauen

MSYS2-Pakete (in PowerShell):

```powershell
cd C:\ABDevelop\CarenDMR
$env:MSYSTEM = "UCRT64"
C:\msys64\usr\bin\bash.exe -lc "pacman -Syu"
C:\msys64\usr\bin\bash.exe -lc "pacman -S --needed mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-cmake mingw-w64-ucrt-x86_64-ninja mingw-w64-ucrt-x86_64-boost"
```

## Einrichten

```powershell
cd C:\ABDevelop
git clone https://github.com/AxBa1964/CarenDMR.git
cd C:\ABDevelop\CarenDMR
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## MD380-Bridge bauen (einmalig bzw. nach Änderungen an `native\`)

```powershell
cd C:\ABDevelop\CarenDMR
powershell -ExecutionPolicy Bypass -File .\native\build_md380_dynarmic_windows.ps1
```

Die Bridge enthält keine Firmware. Beim ersten Start fragt CarenDMR nach dem
Sprach-Codec und lädt die MD380-Firmware auf Wunsch herunter.

## Starten und testen

```powershell
cd C:\ABDevelop\CarenDMR
.\start_gui.bat
.\start_easy.bat
.\.venv\Scripts\python.exe -m pytest tests -q
```

Einstellungen liegen beim Quellcode-Start in `config\` des Projektordners.
Für einen Test wie bei einer Neuinstallation einen leeren Datenordner nutzen:

```powershell
cd C:\ABDevelop\CarenDMR
$env:CARENDMR_DATA_DIR = "$env:TEMP\CarenDMR-Test"
.\.venv\Scripts\python.exe main.py --gui
```

Danach `Remove-Item Env:\CARENDMR_DATA_DIR` oder ein neues PowerShell-Fenster.

## Setup bauen

Doppelklick auf `build_setup.bat` oder:

```powershell
cd C:\ABDevelop\CarenDMR
.\build_setup.bat
```

Einzelheiten in `docs\RELEASE_BUILD.md`.
