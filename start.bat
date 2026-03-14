@echo off
title NexusAI - Full Project Launcher
color 0A

echo ============================================================
echo   NexusAI - Starting Full Project
echo ============================================================
echo.

:: ── Check virtual environment ──────────────────────────────────
if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found.
    echo         Run: python -m venv .venv
    echo         Then: .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1


:: ── Check .env file ────────────────────────────────────────────
if not exist ".env" (
    echo [ERROR] .env file not found.
    echo         Copy .env.example to .env and fill in your API keys.
    pause
    exit /b 1
)

:: ── Check Node / npm ───────────────────────────────────────────
where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] npm not found. Install Node.js from https://nodejs.org
    pause
    exit /b 1
)

:: ── Install frontend deps if node_modules missing ──────────────
if not exist "frontend\node_modules" (
    echo [INFO] Installing frontend dependencies...
    cd frontend
    call npm install
    cd ..
    echo.
)

:: ── Clear Python cache ─────────────────────────────────────────
echo [1/3] Clearing Python cache...
for /d /r src %%d in (__pycache__) do (
    if exist "%%d" rd /s /q "%%d" 2>nul
)
for /d /r api %%d in (__pycache__) do (
    if exist "%%d" rd /s /q "%%d" 2>nul
)
echo       Done.
echo.

:: ── Start Backend (FastAPI) ────────────────────────────────────
echo [2/3] Starting Backend API on http://localhost:8000 ...
start "NexusAI Backend" cmd /k "cd /d %~dp0 && call .venv\Scripts\activate.bat && .venv\Scripts\uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir src --reload-dir api"
echo       Waiting for backend to boot...
timeout /t 4 /nobreak >nul
echo.

:: ── Health check ───────────────────────────────────────────────
echo       Health check...
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:8000/health' -UseBasicParsing -TimeoutSec 8; Write-Host '      [OK] Backend running:' $r.Content } catch { Write-Host '      [WARN] Backend not responding yet - it may still be starting up.' }"
echo.

:: ── Start Frontend (Vite) ──────────────────────────────────────
echo [3/3] Starting Frontend on http://localhost:5173 ...
start "NexusAI Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
echo.

:: ── Done ───────────────────────────────────────────────────────
echo ============================================================
echo   NexusAI is running!
echo.
echo   Frontend  ->  http://localhost:5173
echo   Backend   ->  http://localhost:8000
echo   API Docs  ->  http://localhost:8000/docs
echo   Credits   ->  http://localhost:8000/credits
echo.
echo   Close the Backend and Frontend windows to stop.
echo ============================================================
echo.
pause
