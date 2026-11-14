@echo off
rem CarenDMR starten: Hauptfenster
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Virtuelle Umgebung .venv nicht gefunden.
    echo Bitte zuerst einrichten: python -m venv .venv
    echo und: .venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)

".venv\Scripts\python.exe" main.py --gui
if errorlevel 1 (
    echo.
    echo CarenDMR wurde mit Fehlercode %errorlevel% beendet.
    pause
)
