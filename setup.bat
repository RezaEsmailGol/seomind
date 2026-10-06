@echo off
setlocal

echo.
echo ==========================================
echo   SeoMind Setup - Windows
echo ==========================================
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    set PYTHON=py -3
) else (
    where python >nul 2>nul
    if not %errorlevel%==0 (
        echo [ERROR] Python 3.11 or newer was not found.
        echo Install Python from https://www.python.org/downloads/
        echo Make sure "Add Python to PATH" is enabled.
        pause
        exit /b 1
    )
    set PYTHON=python
)

echo [1/4] Checking Python...
%PYTHON% -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)"
if not %errorlevel%==0 (
    echo [ERROR] SeoMind requires Python 3.11 or newer.
    pause
    exit /b 1
)

echo [2/4] Creating virtual environment...
if not exist .venv (
    %PYTHON% -m venv .venv
)

echo [3/4] Installing SeoMind...
call .venv\Scripts\python.exe -m pip install --upgrade pip
if not %errorlevel%==0 exit /b 1

call .venv\Scripts\python.exe -m pip install -e .
if not %errorlevel%==0 exit /b 1

if not exist .env (
    copy .env.example .env >nul
)

echo [4/4] Starting SeoMind...
echo.
echo SeoMind:  http://127.0.0.1:8787
echo API docs: http://127.0.0.1:8787/docs
echo.
start "" http://127.0.0.1:8787/docs
call .venv\Scripts\seomind.exe

endlocal
