@echo off
setlocal
set "LAUNCHER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\SeoMind.cmd"
if exist "%LAUNCHER%" del "%LAUNCHER%"
echo SeoMind Windows startup entry removed.
endlocal
