@echo off
cd /d "%~dp0"

if not exist ".env" (
    echo .env not found! Rename .env.example to .env and add your API key.
    pause
    exit /b 1
)

py -3 agent.py 2>nul
if errorlevel 1 python agent.py 2>nul
if errorlevel 1 python3 agent.py 2>nul
if errorlevel 1 (
    echo Python not found. Try: Win+R, cmd, py -3 agent.py
)
pause
