@echo off
title Law in Order - Launcher
cd /d "%~dp0"

echo ========================================================
echo   LAW IN ORDER - KB ACADEMY WEBSITE
echo ========================================================
echo.

:: 1. Start the backend in a separate window
echo [1/2] Starting backend API on http://localhost:8000 ...
cd backend
start "Law in Order Backend" cmd /k "uvicorn main:app --reload --port 8000"
cd ..

:: 2. Wait 2 seconds for server startup
timeout /t 2 /nobreak >nul

:: 3. Open the website in the default browser
echo [2/2] Opening website in your browser...
start "" "http://localhost:8000"

echo.
echo ========================================================
echo   Website opened at http://localhost:8000! 
echo   Keep the backend command window open while testing.
echo ========================================================
echo.
pause
