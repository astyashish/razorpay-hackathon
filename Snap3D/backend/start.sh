#!/usr/bin/env bash
# Snap3D Backend Startup Script
# Finds local IP, prints QR code, starts server

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Get local IP address
LOCAL_IP=$(python -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    s.connect(('8.8.8.8', 80))
    ip = s.getsockname()[0]
except Exception:
    ip = socket.gethostbyname(socket.gethostname())
finally:
    s.close()
print(ip)
")

PORT=8000
URL="http://${LOCAL_IP}:${PORT}"

echo ""
echo "╔═══════════════════════════════════════════╗"
echo "║            🎲 Snap3D Server               ║"
echo "╠═══════════════════════════════════════════╣"
echo "║                                           ║"
echo "║  Server URL: ${URL}"
echo "║                                           ║"
echo "║  Scan QR code below with your phone:      ║"
echo "║                                           ║"
echo "╚═══════════════════════════════════════════╝"
echo ""

# Print QR code in terminal
python -c "
import qrcode
qr = qrcode.QRCode(border=1)
qr.add_data('${URL}')
qr.make(fit=True)
qr.print_ascii(invert=True)
"

echo ""
echo "Both devices must be on the same WiFi network."
echo "Starting server on ${URL} ..."
echo ""

cd "$SCRIPT_DIR/.."
python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT --reload
