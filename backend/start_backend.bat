@echo off
title Law in Order - Backend Server
cd /d "%~dp0"
echo.
echo ===================================================
echo   LAW IN ORDER - BACKEND SERVER (FastAPI)
echo   Running at: http://localhost:8000
echo   API Docs at: http://localhost:8000/docs
echo ===================================================
echo.
uvicorn main:app --reload --port 8000
pause
