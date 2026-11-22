@echo off
title OsdagBridge
cd /d "%~dp0src"
echo ===================================================
echo Launching OsdagBridge Desktop Application...
echo ===================================================
call "C:\Users\bohra\anaconda3\Scripts\activate.bat" osdagbridge-env
python -m osdagbridge.desktop
if errorlevel 1 (
    echo.
    echo Application exited with an error.
    pause
)
