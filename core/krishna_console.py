from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

CORE_URL = os.getenv("KRISHNA_CONSOLE_CORE", "http://127.0.0.1:8766").rstrip("/")
PROJECT = os.getenv("KRISHNA_CONSOLE_PROJECT", "general")
STARTUP_ERRORS: list[str] = []


def _request(path: str, payload: dict | None = None, timeout: float = 120.0) -> dict:
    url = CORE_URL + path
    body = None
    headers = {"Accept": "application/json", "X-Krishna-Device": "windows-console"}
    method = "GET"
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
        method = "POST"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            return {"error": json.loads(raw)}
        except Exception:
            return {"error": f"HTTP {exc.code}: {raw}"}
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def _core_ok() -> bool:
    result = _request("/api/status", timeout=2.0)
    return bool(result.get("ok")) and not result.get("error")


def _candidate_core_commands() -> list[list[str]]:
    exe = Path(sys.executable).resolve()
    commands: list[list[str]] = []
    if getattr(sys, "frozen", False):
        here = Path(exe).parent
        commands.extend([
            [str(here / "python.exe"), "-m", "krishna_core.server"],
            ["python", "-m", "krishna_core.server"],
        ])
    else:
        commands.extend([
            [sys.executable, "-m", "krishna_core.server"],
            ["python", "-m", "krishna_core.server"],
        ])
    return commands


def ensure_core() -> bool:
    if _core_ok():
        return True

    # Preferred path for KRISHNA.exe: start the bundled/local Core in-process.
    try:
        from http.server import ThreadingHTTPServer
        from krishna_core.config import settings
        from krishna_core.server import Handler

        server = ThreadingHTTPServer(("127.0.0.1", int(settings.port)), Handler)
        thread = threading.Thread(target=server.serve_forever, name="krishna-core", daemon=True)
        thread.start()
        for _ in range(20):
            time.sleep(0.25)
            if _core_ok():
                return True
    except Exception as exc:
        STARTUP_ERRORS.append(f"in-process core: {type(exc).__name__}: {exc}")

    # Source-development fallback.
    env = os.environ.copy()
    env.setdefault("KRISHNA_HOST", "127.0.0.1")
    env.setdefault("KRISHNA_PORT", "8766")
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    for command in _candidate_core_commands():
        try:
            subprocess.Popen(
                command,
                cwd=str(Path.cwd()),
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
            for _ in range(16):
                time.sleep(0.25)
                if _core_ok():
                    return True
        except Exception as exc:
            STARTUP_ERRORS.append(
                "fallback " + " ".join(command) + f": {type(exc).__name__}: {exc}"
            )
            continue
    return False


def banner() -> None:
    print()
    print("  ██╗  ██╗██████╗ ██╗███████╗██╗  ██╗███╗   ██╗ █████╗ ")
    print("  ██║ ██╔╝██╔══██╗██║██╔════╝██║  ██║████╗  ██║██╔══██╗")
    print("  █████╔╝ ██████╔╝██║███████╗███████║██╔██╗ ██║███████║")
    print("  ██╔═██╗ ██╔══██╗██║╚════██║██╔══██║██║╚██╗██║██╔══██║")
    print("  ██║  ██╗██║  ██║██║███████║██║  ██║██║ ╚████║██║  ██║")
    print("  ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝")
    print()
    print("  Your AI. Your Control. Always With You.")
    print("  Conversation console · Local autonomous operator")
    print("  Type /help for commands. Type /exit to close.")
    print()


def pretty(value) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, indent=2, ensure_ascii=False)


def command(line: str, project: str) -> tuple[bool, str]:
    parts = line.strip().split(maxsplit=2)
    cmd = parts[0].lower()

    if cmd in {"/exit", "/quit"}:
        return False, project

    if cmd == "/help":
        print("""Commands:
  /status                 Core + watcher + resource status
  /project NAME           Set active project for conversation
  /projects               List registered projects
  /inspect URL            Inspect a running web UI in Chromium
  /investigate TEXT       Collect evidence + root-cause hypotheses
  /research QUERY         Research GitHub components for active project
  /index                   Index active project repository
  /incidents               Show recent project incidents
  /clear                   Clear console
  /exit                    Close KRISHNA
Anything else is sent as a normal conversation to KRISHNA.
""")
        return True, project

    if cmd == "/clear":
        os.system("cls" if os.name == "nt" else "clear")
        banner()
        return True, project

    if cmd == "/project":
        if len(parts) < 2:
            print(f"Active project: {project}")
            return True, project
        project = parts[1].strip()
        print(f"Active project -> {project}")
        return True, project

    if cmd == "/status":
        print(pretty(_request("/api/status")))
        return True, project

    if cmd == "/projects":
        print(pretty(_request("/api/projects")))
        return True, project

    if cmd == "/index":
        print(pretty(_request("/api/projects/index", {"project": project})))
        return True, project

    if cmd == "/incidents":
        print(pretty(_request(f"/api/incidents?project={urllib.parse.quote(project)}")))
        return True, project

    if cmd == "/investigate":
        if len(parts) < 2:
            print("Usage: /investigate <problem>")
        else:
            text = line.split(maxsplit=1)[1]
            print(pretty(_request("/api/investigate", {"project": project, "symptom": text})))
        return True, project

    if cmd == "/inspect":
        if len(parts) < 2:
            print("Usage: /inspect <http://...>")
        else:
            url = line.split(maxsplit=1)[1]
            print(pretty(_request("/api/browser/inspect", {"project": project, "url": url})))
        return True, project

    if cmd == "/research":
        if len(parts) < 2:
            print("Usage: /research <what capability/component to find>")
        else:
            query = line.split(maxsplit=1)[1]
            print(pretty(_request("/api/research/github", {"project": project, "query": query})))
        return True, project

    print(f"Unknown command: {cmd}. Type /help.")
    return True, project


def chat(text: str, project: str) -> None:
    result = _request("/api/core/chat", {
        "message": text,
        "project": project,
        "source": "windows-console",
    })
    if result.get("error"):
        print(f"KRISHNA ERROR> {pretty(result['error'])}")
        return
    answer = result.get("text") or result.get("reply") or result
    print(f"KRISHNA> {pretty(answer)}")


def main() -> int:
    global PROJECT
    banner()
    if not ensure_core():
        print("KRISHNA> Core could not start automatically.")
        if STARTUP_ERRORS:
            print("KRISHNA> Startup diagnostics:")
            for err in STARTUP_ERRORS[-5:]:
                print("  - " + err)
        print("KRISHNA> Type /status after correcting the reported startup problem.")
    else:
        print("KRISHNA> Core connected. Radhe Radhe.")
    print()

    project = PROJECT
    while True:
        try:
            line = input(f"YOU [{project}]> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nKRISHNA> Closing console.")
            return 0
        if not line:
            continue
        if line.startswith("/"):
            keep_running, project = command(line, project)
            if not keep_running:
                print("KRISHNA> Radhe Radhe.")
                return 0
            continue
        chat(line, project)
        print()


if __name__ == "__main__":
    raise SystemExit(main())
