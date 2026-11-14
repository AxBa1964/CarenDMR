@echo off
setlocal
cd /d "%~dp0" || exit /b 1

if not exist ".venv\Scripts\activate.bat" goto :missing_venv
if not exist ".venv\Scripts\python.exe" goto :missing_venv

call ".venv\Scripts\activate.bat"
".venv\Scripts\python.exe" "main.py" --gui
set "gui_exit=%errorlevel%"
if "%gui_exit%"=="0" exit /b 0

echo CarenDMR wurde mit Fehlercode %gui_exit% beendet.
pause
exit /b %gui_exit%

:missing_venv
echo Die Python-Umgebung .venv fehlt oder ist unvollstaendig.
echo Die Einrichtung ist in INSTALL_WINDOWS.md beschrieben.
pause
exit /b 1
