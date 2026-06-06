@echo off
REM NetWatch — Windows Startup Script
REM Starts both Python backend and Node.js frontend

setlocal enabledelayedexpansion

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║            NetWatch — Network Monitor                    ║
echo ║       Starting Python Backend + Node.js Frontend         ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.9+ from https://www.python.org
    pause
    exit /b 1
)

REM Check for Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js is not installed or not in PATH
    echo Please install Node.js 18+ from https://nodejs.org
    pause
    exit /b 1
)

REM Load .env if exists
if not exist .env (
    echo ⚠️  .env file not found, using defaults
    echo Creating .env from .env.example...
    if exist .env.example (
        copy .env.example .env
    ) else (
        echo BACKEND_API_URL=http://localhost:8000 > .env
        echo NODE_PORT=3000 >> .env
        echo PYTHON_PORT=8000 >> .env
    )
)

echo ▶️  Starting Python backend (Port 8000)...
echo   ⚠️  IMPORTANT: Requires Administrator privileges for packet capture!
echo.

REM Start Python backend in new window
cd backend\python
start cmd /k "pip install -r requirements.txt -q && python api_server.py"
cd ..\..

timeout /t 3 /nobreak

echo ▶️  Starting Node.js frontend (Port 3000)...
echo.

REM Start Node.js frontend in new window
start cmd /k "npm install -q && npm start"

echo.
echo ✅ Both services starting...
echo.
echo 🌐 Dashboard:  http://localhost:3000
echo 📡 Backend:    http://localhost:8000
echo 📖 API Docs:   http://localhost:8000/docs
echo.
echo Press any key to open dashboard in browser...
pause

start http://localhost:3000

echo Done!
