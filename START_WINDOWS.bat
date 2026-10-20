@echo off
cd /d %~dp0
if not exist .venv (py -m venv .venv)
call .venv\Scripts\activate.bat
python -m pip install -r backend\requirements.txt
if errorlevel 1 (echo Installation failed. & pause & exit /b 1)
echo.
echo DEMO ONLY - NO REAL PATIENT OR PAYMENT DATA.
echo Open http://127.0.0.1:8000 in your browser.
echo.
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
pause
