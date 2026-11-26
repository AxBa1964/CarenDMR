@echo off
rem CarenDMR: Tests ausfuehren, Exe und Installer bauen.
rem Ergebnis: release\installer\CarenDMR-Setup-<Version>.exe
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Virtuelle Umgebung .venv nicht gefunden. Siehe docs\ENTWICKLUNG.md
    pause
    exit /b 1
)

echo.
echo === 1/2 Tests ===
".venv\Scripts\python.exe" -m pytest tests -q
if errorlevel 1 (
    echo.
    echo Tests fehlgeschlagen - es wurde KEIN Setup gebaut.
    pause
    exit /b 1
)

echo.
echo === 2/2 Exe und Installer bauen ===
powershell -NoProfile -ExecutionPolicy Bypass -File "packaging\build_release.ps1"
if errorlevel 1 (
    echo.
    echo Bau fehlgeschlagen - Meldung oben beachten.
    pause
    exit /b 1
)

echo.
echo Fertig. Der Ordner mit dem Setup wird geoeffnet.
start "" explorer "%~dp0release\installer"
pause
