@echo off
setlocal
cd /d "%~dp0"

if not exist .venv\Scripts\pythonw.exe (
  echo [ERROR] SeoMind virtual environment was not found.
  exit /b 1
)

set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "LAUNCHER=%STARTUP%\SeoMind.cmd"

> "%LAUNCHER%" echo @echo off
>> "%LAUNCHER%" echo cd /d "%CD%"
>> "%LAUNCHER%" echo start "" "%CD%\.venv\Scripts\pythonw.exe" -m seomind.tray

echo SeoMind will now start with Windows and stay in the system tray.
echo Startup launcher: %LAUNCHER%
endlocal
