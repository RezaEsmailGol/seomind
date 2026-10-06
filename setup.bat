@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo.
echo =====================================================
echo   SeoMind Setup - Windows
echo =====================================================
echo.

where py >nul 2>nul
if %errorlevel%==0 (
  set "PYTHON=py -3"
) else (
  where python >nul 2>nul
  if not %errorlevel%==0 (
    echo [ERROR] Python 3.11+ was not found.
    echo Install it from https://www.python.org/downloads/
    pause
    exit /b 1
  )
  set "PYTHON=python"
)

where node >nul 2>nul
if not %errorlevel%==0 (
  echo [ERROR] Node.js 20+ was not found.
  echo Install the current Node.js LTS release.
  pause
  exit /b 1
)

where npm >nul 2>nul
if not %errorlevel%==0 (
  echo [ERROR] npm was not found.
  pause
  exit /b 1
)

echo [1/7] Checking Python...
%PYTHON% -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)"
if not %errorlevel%==0 (
  echo [ERROR] SeoMind requires Python 3.11 or newer.
  pause
  exit /b 1
)

echo [2/7] Checking Node.js...
node -e "const m=Number(process.versions.node.split('.')[0]); process.exit(m >= 20 ? 0 : 1)"
if not %errorlevel%==0 (
  echo [ERROR] SeoMind requires Node.js 20 or newer.
  pause
  exit /b 1
)

echo [3/7] Creating Python environment...
if not exist .venv %PYTHON% -m venv .venv
call .venv\Scripts\python.exe -m pip install --upgrade pip
if not %errorlevel%==0 exit /b 1
call .venv\Scripts\python.exe -m pip install -e .
if not %errorlevel%==0 exit /b 1

if not exist .env copy .env.example .env >nul

echo [4/7] Installing web interface...
pushd apps\web
if not exist .env.local copy .env.local.example .env.local >nul
call npm install
if not %errorlevel%==0 (
  popd
  exit /b 1
)

echo [5/7] Building web interface...
call npm run build
if not %errorlevel%==0 (
  popd
  exit /b 1
)
popd

echo [6/7] Enabling SeoMind at Windows startup...
call install-startup.bat

echo [7/7] Starting SeoMind tray assistant...
call start-tray.bat
timeout /t 3 /nobreak >nul
start "" http://127.0.0.1:3000

echo.
echo SeoMind is installed and will stay available in the Windows system tray.
echo Use uninstall-startup.bat if you do not want it to start with Windows.
echo.
endlocal
