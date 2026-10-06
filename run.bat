@echo off
setlocal
cd /d "%~dp0"

if not exist .venv\Scripts\seomind.exe (
  echo SeoMind is not installed. Run setup.bat first.
  pause
  exit /b 1
)
if not exist apps\web\node_modules (
  echo Web dependencies are not installed. Run setup.bat first.
  pause
  exit /b 1
)

echo Starting SeoMind API on http://127.0.0.1:8787
start "SeoMind API" /D "%~dp0" cmd /k ".venv\Scripts\seomind.exe"

echo Starting SeoMind Web on http://127.0.0.1:3000
start "SeoMind Web" /D "%~dp0apps\web" cmd /k "npm start"

timeout /t 3 /nobreak >nul
start "" http://127.0.0.1:3000
endlocal
