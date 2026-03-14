@echo off
title Shop Quality System

set APP_DIR=C:\Users\computer\OneDrive\shop_quality_system

echo [1/3] Starting Flask server...
start "" /min cmd /c "cd /d %APP_DIR% && py app.py"

timeout /t 5 >nul

echo.
echo [2/3] Starting NGROK tunnel...
start cmd /k "ngrok http 5000"

timeout /t 3 >nul

echo.
echo ================= MOBILE LINK =================
echo Look for this line in the window above:
echo Forwarding https://xxxx.ngrok-free.app
echo ==============================================

pause