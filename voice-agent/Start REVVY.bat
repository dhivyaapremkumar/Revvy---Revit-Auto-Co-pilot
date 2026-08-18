@echo off
title REVVY Voice Agent
cd /d "%~dp0"
".venv\Scripts\python.exe" main.py
if errorlevel 1 (
    echo.
    echo REVVY exited with an error -- see above.
    pause
)
