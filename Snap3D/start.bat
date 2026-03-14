@echo off
REM ============================================================
REM  Snap3D -- One-click launcher for Windows
REM  Usage: double-click this file
REM ============================================================
title Snap3D Launcher

REM Enable UTF-8 so QR code Unicode blocks render correctly
chcp 65001 > nul

set ROOT=%~dp0
set VENV_PYTHON=%ROOT%.venv\Scripts\python.exe
set API_PORT=8001
set FE_PORT=5173

REM ── Validate venv ─────────────────────────────────────────
if not exist "%VENV_PYTHON%" (
    echo.
    echo  ERROR: Python virtual environment not found.
    echo  Expected: %VENV_PYTHON%
    echo.
    echo  To set it up, run these commands once:
    echo    python -m venv .venv
    echo    .venv\Scripts\pip install -r backend\requirements.txt
    echo.
    pause
    exit /b 1
)

cls

REM ── Print server info + QR code ───────────────────────────
"%VENV_PYTHON%" "%ROOT%tools\show_info.py" %API_PORT% %FE_PORT%

REM ── Start backend in its own CMD window ───────────────────
start "Snap3D Backend" cmd /k "chcp 65001 > nul && title Snap3D Backend [port %API_PORT%] && cd /d "%ROOT%" && echo Starting TripoSR backend... && "%VENV_PYTHON%" -m uvicorn backend.main:app --host 0.0.0.0 --port %API_PORT%"

REM ── Start frontend dev server in its own CMD window ───────
start "Snap3D Frontend" cmd /k "title Snap3D Frontend [port %FE_PORT%] && cd /d "%ROOT%frontend" && echo Starting Vite frontend... && npm run dev"

REM ── Wait for servers to come up, then open browser ────────
echo  Waiting for servers to start...
timeout /t 6 /nobreak > nul
start "" "http://localhost:%FE_PORT%"

echo.
echo  ============================================================
echo   Both servers are running in their own windows.
echo   Browser opened at http://localhost:%FE_PORT%
echo.
echo   To stop everything: close the Backend and Frontend windows.
echo  ============================================================
echo.
pause > nul

