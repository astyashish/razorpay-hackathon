"""
Snap3D – terminal startup info + QR code printer.
Called by start.bat: python tools\show_info.py <api_port> <frontend_port>
"""
import sys
import socket

API_PORT = sys.argv[1] if len(sys.argv) > 1 else "8001"
FE_PORT  = sys.argv[2] if len(sys.argv) > 2 else "5173"


def get_lan_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def force_utf8():
    """Re-open stdout in UTF-8 so Unicode block chars render for QR code."""
    if sys.platform == "win32":
        import io
        try:
            sys.stdout = io.TextIOWrapper(
                sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
            )
        except AttributeError:
            pass  # already wrapped


def print_qr_unicode(url: str):
    """Print QR code using Unicode block chars (requires chcp 65001 / UTF-8 terminal)."""
    import qrcode
    qr = qrcode.QRCode(
        border=2,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
    )
    qr.add_data(url)
    qr.make(fit=True)
    qr.print_ascii(invert=True)


def print_qr_ascii(url: str):
    """Fallback: print QR using ## / '  ' characters (pure ASCII, always works)."""
    import qrcode
    qr = qrcode.QRCode(
        border=2,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
    )
    qr.add_data(url)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    for row in matrix:
        print("  " + "".join("  " if cell else "\u2588\u2588" for cell in row))


def main():
    force_utf8()

    ip = get_lan_ip()
    api_url = f"http://{ip}:{API_PORT}"
    fe_url  = f"http://{ip}:{FE_PORT}"

    W = 52
    print()
    print("  " + "=" * W)
    print("  |" + "  S N A P 3 D  -  Server Ready".center(W - 2) + "|")
    print("  " + "=" * W)
    print(f"  | {'PC  (open in browser):':<20}  {'http://localhost:' + FE_PORT:<27}|")
    print(f"  | {'Backend API:':<20}  {'http://localhost:' + API_PORT:<27}|")
    print("  |" + "-" * (W - 2) + "|")
    print(f"  | {'WiFi / LAN (phone):':<20}  {api_url:<27}|")
    print(f"  | {'Frontend (phone):':<20}  {fe_url:<27}|")
    print("  " + "=" * W)
    print()
    print("  >> On this PC: browser opens automatically at http://localhost:" + FE_PORT)
    print("  >> On a phone: scan the QR code below, THEN enter the WiFi URL in the app")
    print()

    try:
        print_qr_unicode(api_url)
    except Exception:
        try:
            print_qr_ascii(api_url)
        except Exception as e:
            print(f"  [QR code unavailable: {e}]")
            print(f"  Enter manually in app: {api_url}")

    print()
    print(f"  Phone app server URL: {api_url}")
    print()


if __name__ == "__main__":
    main()
