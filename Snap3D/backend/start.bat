@echo off
REM Snap3D Backend Startup Script for Windows
REM Finds local IP, prints QR code, starts server

cd /d "%~dp0"

echo.
echo ========================================
echo          Snap3D Server
echo ========================================

REM Resolve venv Python (check for .venv in parent directory)
set VENV_PYTHON=%~dp0\..\\.venv\Scripts\python.exe
if not exist "%VENV_PYTHON%" (
    echo WARNING: venv not found at %VENV_PYTHON%
    echo Falling back to system Python. Activate your venv first if needed.
    set VENV_PYTHON=python
)

REM Get local IP address
for /f "tokens=*" %%i in ('%VENV_PYTHON% -c "import socket; s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.connect((chr(56)+chr(46)+chr(56)+chr(46)+chr(56)+chr(46)+chr(56),80)); print(s.getsockname()[0]); s.close()"') do set LOCAL_IP=%%i

set PORT=8001
set URL=http://%LOCAL_IP%:%PORT%

echo.
echo   Server URL: %URL%
echo.
echo   Scan this QR code with your phone:
echo.

%VENV_PYTHON% -c "import qrcode; qr=qrcode.QRCode(border=1); qr.add_data('%URL%'); qr.make(fit=True); qr.print_ascii(invert=True)"

echo.
echo   Both devices must be on the same WiFi network.
echo   Starting server...
echo.

cd /d "%~dp0\.."
"%VENV_PYTHON%" -m uvicorn backend.main:app --host 0.0.0.0 --port %PORT% --reload
