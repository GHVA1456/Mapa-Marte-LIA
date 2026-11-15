@echo off
rem Double-click to start MARS-NAV. The first run sets up the .venv virtual environment.
cd /d "%~dp0"
py app.py 2>nul || python app.py
pause
