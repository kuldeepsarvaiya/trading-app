"""
Launcher for AlphaTrader Mobile Web Server & PWA.
Prints mobile access links and starts Uvicorn.
"""

import os
import sys
import socket
import uvicorn


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


if __name__ == "__main__":
    local_ip = get_local_ip()
    port = int(os.environ.get("PORT", 8000))

    print("\n" + "=" * 60)
    print("  🚀 ALPHATRADER MOBILE PWA & ALGO BOT SERVER")
    print("=" * 60)
    print(f"  💻 Local PC URL   :  http://localhost:{port}")
    print(f"  📱 Mobile Phone URL:  http://{local_ip}:{port}")
    print("=" * 60)
    print("  🔒 Default Office PIN: 1234")
    print("  📲 On phone: Open the Mobile Phone URL in Chrome/Safari")
    print("     and tap 'Add to Home Screen' for standalone App mode!")
    print("=" * 60 + "\n")

    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
