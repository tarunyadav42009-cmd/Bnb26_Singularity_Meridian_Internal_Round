@echo off
setlocal

cd /d "%~dp0"

echo.
echo  ==========================================
echo       QUORUM - Build Integrity Console
echo  ==========================================
echo.

REM ==========================================
REM Find Python
REM ==========================================

where python >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    goto python_found
)

where py >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_CMD=py"
    goto python_found
)

echo ERROR: Python was not found.
echo Please install Python 3.11+ and make sure Python is added to PATH.
echo.
pause
exit /b 1

:python_found

echo Python launcher found: %PYTHON_CMD%
%PYTHON_CMD% --version
echo.

REM ==========================================
REM Create virtual environment
REM ==========================================

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creating virtual environment...
    %PYTHON_CMD% -m venv .venv

    if errorlevel 1 (
        echo.
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo [1/3] Virtual environment already exists.
)

REM ==========================================
REM Install dependencies
REM ==========================================

echo.
echo [2/3] Installing/checking dependencies...

".venv\Scripts\python.exe" -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR: Dependency installation failed.
    pause
    exit /b 1
)

REM ==========================================
REM Start QUORUM
REM ==========================================

echo.
echo [3/3] Starting QUORUM...
echo.
echo Keep this window open.
echo Open http://127.0.0.1:5000/ in your browser.
echo Press Ctrl+C to stop the server.
echo.

".venv\Scripts\python.exe" -m backend.app

if errorlevel 1 (
    echo.
    echo ERROR: QUORUM server stopped unexpectedly.
    pause
    exit /b 1
)

exit /b 0