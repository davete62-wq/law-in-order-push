@echo off
title Law in Order - Initialize Database
cd /d "%~dp0"
echo.
echo ===================================================
echo   LAW IN ORDER - INITIALIZE DATABASE TABLES
echo ===================================================
echo.
python setup_db.py
echo.
pause
