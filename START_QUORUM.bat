@echo off
setlocal
cd /d "%~dp0"
echo.
echo  ==========================================
echo       QUORUM - Build Integrity Console
echo  ==========================================
echo.
where py >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python launcher 'py' was not found.
  echo Install Python 3.11+ from https://www.python.org/downloads/
  echo Then run this file again.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Creating virtual environment...
  py -m venv .venv
  if errorlevel 1 goto failed
)
echo [2/3] Installing/checking dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo.
echo [3/3] Starting QUORUM...
echo Keep this window open. Open http://127.0.0.1:5000/ in your browser.
echo Press Ctrl+C to stop the server.
echo.
".venv\Scripts\python.exe" -m backend.app
if errorlevel 1 goto failed
exit /b 0
:failed
echo.
echo Setup or startup failed. Read SETUP_GUIDE.md for troubleshooting.
pause
exit /b 1
