@echo off
setlocal
cd /d "%~dp0"

if not exist .venv\Scripts\pythonw.exe (
  echo SeoMind is not installed. Run setup.bat first.
  exit /b 1
)

start "" ".venv\Scripts\pythonw.exe" -m seomind.tray
endlocal
