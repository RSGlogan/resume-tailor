@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================
echo    Tailor - AI Resume Tailorer
echo ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [!] Python is not installed or not on PATH.
  echo     Download it from https://www.python.org/downloads/
  echo     During install, CHECK "Add Python to PATH".
  echo.
  pause
  exit /b
)

if not exist ".venv" (
  echo First-time setup: creating a local environment...
  python -m venv .venv
)
call ".venv\Scripts\activate.bat"

echo Checking dependencies (first run may take a minute)...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

if not exist ".env" (
  echo.
  echo One-time setup: paste your FREE Gemini API key below.
  echo   Get one at https://aistudio.google.com   ^(no credit card needed^)
  echo.
  set /p APIKEY="Gemini API key: "
  > .env echo GEMINI_API_KEY=!APIKEY!
  echo Saved locally to .env  ^(never shared^).
)

echo.
echo Starting Tailor...  Your browser will open automatically.
echo Close this window to stop the app.
echo.
python app.py

pause
