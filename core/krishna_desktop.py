from __future__ import annotations

import sys
import time
import webbrowser

from krishna_console import ensure_core, STARTUP_ERRORS

CONTROL_ROOM = "http://127.0.0.1:8766/web"

def _wait_for_core(timeout=20.0):
    if not ensure_core():
        return False
    deadline=time.time()+timeout
    while time.time()<deadline:
        try:
            import urllib.request
            with urllib.request.urlopen("http://127.0.0.1:8766/health",timeout=1.5) as r:
                if r.status==200:return True
        except Exception:
            time.sleep(.35)
    return False

def main():
    if not _wait_for_core():
        detail="\n".join(STARTUP_ERRORS[-8:]) or "KRISHNA Core did not become ready."
        raise RuntimeError(detail)
    try:
        import webview
        webview.create_window(
            "KRISHNA · Control Room",
            CONTROL_ROOM,
            width=1480,
            height=920,
            min_size=(1050,700),
            background_color="#050b12",
        )
        webview.start(debug=False)
    except Exception:
        webbrowser.open(CONTROL_ROOM)
        if getattr(sys,"frozen",False):
            time.sleep(3)

if __name__=="__main__":
    main()
