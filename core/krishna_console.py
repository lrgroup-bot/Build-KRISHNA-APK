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


def _new_chat(project: str, title: str = "New chat") -> dict:
    return _request("/api/chats/create", {"project": project, "title": title})


def _latest_chat(project: str) -> dict | None:
    result = _request(f"/api/chats?project={urllib.parse.quote(project)}")
    chats = result.get("chats") or []
    return chats[0] if chats else None


def ensure_chat(project: str, title: str = "General") -> str | None:
    latest = _latest_chat(project)
    if latest:
        return latest.get("chat_id")
    created = _new_chat(project, title)
    return created.get("chat_id") if not created.get("error") else None


def _chat_label(chat_id: str | None) -> str:
    if not chat_id:
        return "no-chat"
    return chat_id.split("-", 1)[0]


def command(line: str, project: str, chat_id: str | None) -> tuple[bool, str, str | None]:
    parts = line.strip().split(maxsplit=2)
    cmd = parts[0].lower()

    if cmd in {"/exit", "/quit"}:
        return False, project, chat_id

    if cmd == "/help":
        print("""Commands:
  /newproject NAME ROOT   Create/register a persistent project workspace
  /project NAME           Switch project and open its latest chat
  /projects               List persistent projects
  /newchat TITLE          Create a new chat inside the active project
  /chats                  List chats inside the active project
  /chat CHAT_ID           Switch to a specific project chat
  /history                Show stored messages in the active chat
  /status                 Core + watcher + resource status
  /engines                Show all KRISHNA Core capabilities loaded in this EXE
  /index                  Index active project repository
  /inspect URL            Inspect the real UI in Chrome/Chromium
  /investigate TEXT       Collect evidence + root-cause hypotheses
  /research QUERY         Research GitHub components for active project
  /incidents              Show learned project incidents
  /clear                  Clear console
  /exit                   Close KRISHNA
Anything else is a normal persistent conversation with KRISHNA.
""")
        return True, project, chat_id

    if cmd == "/clear":
        os.system("cls" if os.name == "nt" else "clear")
        banner()
        return True, project, chat_id

    if cmd == "/newproject":
        if len(parts) < 3:
            print("Usage: /newproject <NAME> <ROOT_PATH>")
            return True, project, chat_id
        name = parts[1].strip()
        root = parts[2].strip().strip('"')
        result = _request("/api/projects/register", {
            "name": name,
            "root": root,
            "privacy": "local_only",
            "allowed_actions": [],
            "verification_checks": [],
            "metadata": {"created_from": "KRISHNA.exe"},
        })
        if result.get("error"):
            print(pretty(result))
            return True, project, chat_id
        project = name
        chat_id = ensure_chat(project, "Project start")
        print(f"Project created -> {project}")
        print(f"Active chat -> {_chat_label(chat_id)}")
        return True, project, chat_id

    if cmd == "/project":
        if len(parts) < 2:
            print(f"Active project: {project}")
            print(f"Active chat: {_chat_label(chat_id)}")
            return True, project, chat_id
        project = parts[1].strip()
        chat_id = ensure_chat(project, "Project chat")
        if chat_id:
            print(f"Active project -> {project}")
            print(f"Active chat -> {_chat_label(chat_id)}")
        else:
            print(f"Unable to open project '{project}'. Register it first with /newproject.")
        return True, project, chat_id

    if cmd == "/newchat":
        title = line.split(maxsplit=1)[1].strip() if len(parts) >= 2 else "New chat"
        result = _new_chat(project, title)
        if result.get("error"):
            print(pretty(result))
        else:
            chat_id = result.get("chat_id")
            print(f"New chat -> {result.get('title')} [{_chat_label(chat_id)}]")
        return True, project, chat_id

    if cmd == "/chats":
        print(pretty(_request(f"/api/chats?project={urllib.parse.quote(project)}")))
        return True, project, chat_id

    if cmd == "/chat":
        if len(parts) < 2:
            print(f"Active chat: {_chat_label(chat_id)}")
            return True, project, chat_id
        candidate = parts[1].strip()
        history = _request(f"/api/chat/history?chat_id={urllib.parse.quote(candidate)}")
        if history.get("error"):
            print(pretty(history))
        else:
            chat_id = candidate
            print(f"Active chat -> {_chat_label(chat_id)}")
        return True, project, chat_id

    if cmd == "/history":
        if not chat_id:
            print("No active chat.")
        else:
            print(pretty(_request(f"/api/chat/history?chat_id={urllib.parse.quote(chat_id)}")))
        return True, project, chat_id

    if cmd == "/status":
        print(pretty(_request("/api/status")))
        return True, project, chat_id

    if cmd == "/engines":
        print(pretty(_request("/api/capabilities")))
        return True, project, chat_id

    if cmd == "/projects":
        print(pretty(_request("/api/projects")))
        return True, project, chat_id

    if cmd == "/index":
        print(pretty(_request("/api/projects/index", {"project": project})))
        return True, project, chat_id

    if cmd == "/incidents":
        print(pretty(_request(f"/api/incidents?project={urllib.parse.quote(project)}")))
        return True, project, chat_id

    if cmd == "/investigate":
        if len(parts) < 2:
            print("Usage: /investigate <problem>")
        else:
            text = line.split(maxsplit=1)[1]
            print(pretty(_request("/api/investigate", {"project": project, "symptom": text})))
        return True, project, chat_id

    if cmd == "/inspect":
        if len(parts) < 2:
            print("Usage: /inspect <http://...>")
        else:
            url = line.split(maxsplit=1)[1]
            print(pretty(_request("/api/browser/inspect", {"project": project, "url": url})))
        return True, project, chat_id

    if cmd == "/research":
        if len(parts) < 2:
            print("Usage: /research <what capability/component to find>")
        else:
            query = line.split(maxsplit=1)[1]
            print(pretty(_request("/api/research/github", {"project": project, "query": query})))
        return True, project, chat_id

    print(f"Unknown command: {cmd}. Type /help.")
    return True, project, chat_id


def chat(text: str, project: str, chat_id: str | None) -> None:
    result = _request("/api/core/chat", {
        "message": text,
        "project": project,
        "chat_id": chat_id,
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
    chat_id = ensure_chat(project, "General")
    if chat_id:
        print(f"KRISHNA> Active workspace: {project} / {_chat_label(chat_id)}")
        print()
    while True:
        try:
            line = input(f"YOU [{project} | {_chat_label(chat_id)}]> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nKRISHNA> Closing console.")
            return 0
        if not line:
            continue
        if line.startswith("/"):
            keep_running, project, chat_id = command(line, project, chat_id)
            if not keep_running:
                print("KRISHNA> Radhe Radhe.")
                return 0
            continue
        chat(line, project, chat_id)
        print()


if __name__ == "__main__":
    raise SystemExit(main())
