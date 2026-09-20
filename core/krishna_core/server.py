from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import json, time, threading, base64, sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from .config import settings
from .orchestrator import Orchestrator
from .watcher import Watcher
from .pc_observer import PCObserver
from .device_pairing import DevicePairingStore
from .realtime_session import RealtimeSessionStore
from .plugin_runtime import PluginRegistry
from .plugin_executor import PluginExecutor
from .attachments import AttachmentStore
from .specialist_library import SpecialistLibrary

orch = Orchestrator()
_pairing = DevicePairingStore(Path(settings.db_path).resolve().parent / ".krishna_state")
_sessions = RealtimeSessionStore(Path(settings.db_path).resolve().parent / ".krishna_state")
_plugins = PluginRegistry(Path(settings.db_path).resolve().parent / ".krishna_state")
_plugin_executor = PluginExecutor(_plugins)
_attachments = AttachmentStore(Path(settings.db_path).resolve().parent / ".krishna_state")
_specialists = SpecialistLibrary(Path(settings.db_path).resolve().parent / ".krishna_state", Path(__file__).resolve().parents[2] / "external" / "agency-agents")
try:
    if _specialists.source_root.exists():
        _specialists.index()
except Exception:
    pass
started = time.time()
activity = {"current_activity": "Idle", "updated": time.strftime("%Y-%m-%d %H:%M:%S"), "recent": []}
_mobile_lock = threading.RLock()
_mobile_link = {
    "device": None,
    "last_seen": 0.0,
    "last_path": None,
    "requests": 0,
}


def touch_mobile(device, path):
    if not device:
        return
    now = time.time()
    with _mobile_lock:
        _mobile_link["device"] = str(device)[:128]
        _mobile_link["last_seen"] = now
        _mobile_link["last_path"] = str(path)[:256]
        _mobile_link["requests"] += 1


def mobile_link_state():
    now = time.time()
    with _mobile_lock:
        last_seen = float(_mobile_link["last_seen"] or 0.0)
        age = None if not last_seen else max(0.0, now - last_seen)
        return {
            **_mobile_link,
            "connected": bool(last_seen and age <= 20.0),
            "age_seconds": None if age is None else round(age, 1),
        }
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    _BUNDLE_ROOT = Path(sys._MEIPASS)
    DASHBOARD = _BUNDLE_ROOT / "dashboard.html"
    WEB_VALIDATION = _BUNDLE_ROOT / "web_validation.html"
    AVATAR_B64 = _BUNDLE_ROOT / "avatar" / "krishna_child_360.webp.b64"
    AVATAR_GLB = _BUNDLE_ROOT / "avatar" / "krishna.glb"
else:
    _CORE_ROOT = Path(__file__).resolve().parents[1]
    _REPO_ROOT = Path(__file__).resolve().parents[2]
    DASHBOARD = _CORE_ROOT / "dashboard.html"
    WEB_VALIDATION = _CORE_ROOT / "web_validation.html"
    AVATAR_B64 = _REPO_ROOT / "avatar" / "krishna_child_360.webp.b64"
    AVATAR_GLB = _CORE_ROOT.parent / "dashboard" / "assets" / "avatar" / "krishna.glb"


def avatar_360_bytes():
    try:
        return base64.b64decode(AVATAR_B64.read_text(encoding="utf-8").strip(), validate=True)
    except Exception:
        return b""


def mark(event, detail=""):
    now = time.strftime("%H:%M:%S")
    activity["current_activity"] = detail or event
    activity["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    activity["recent"].insert(0, {"time": now, "event": event + ((": " + detail) if detail else "")})
    del activity["recent"][30:]


def on_transition(transition):
    target = transition["target"]
    status = "UP" if transition["to"] else "DOWN"
    mark("WATCHER TRANSITION", f"{target} -> {status}")
    orch.memory.remember("system", "watcher_transition", f"{target} -> {status}", transition)
    orch.memory.audit("watcher", "transition", json.dumps(transition))
    orch.handle_event(
        "pc_watcher", "service_recovered" if transition["to"] else "service_down",
        f"{target} -> {status}", severity="notice" if transition["to"] else "critical",
        project="system", payload=transition,
    )


watcher = Watcher(on_transition=on_transition)
watcher.start()

def on_pc_event(event):
    orch.handle_event(
        event.get("source", "pc_observer"),
        event.get("kind", "event"),
        event.get("detail", ""),
        severity=event.get("severity", "info"),
        project=event.get("project", "system"),
        payload=event.get("payload") or {},
    )

pc_observer = PCObserver(
    orch.projects.list,
    on_event=on_pc_event,
    cpu_budget_percent=orch.governor.cpu_budget,
    memory_budget_percent=orch.governor.memory_budget,
)
pc_observer.start()


class Handler(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _binary(self, code, body, content_type):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "public, max-age=3600")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, code, text):
        b = text.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _body(self):
        n = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(n) or b"{}")

    def _device_auth(self):
        device = self.headers.get("X-Krishna-Device", "").strip()
        auth = self.headers.get("Authorization", "")
        token = auth[7:].strip() if auth.startswith("Device ") else ""
        return device, token

    def do_GET(self):
        touch_mobile(self.headers.get("X-Krishna-Device"), self.path)
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path in ("/", "/dashboard"):
            return self._html(200, DASHBOARD.read_text(encoding="utf-8"))
        if path in ("/web", "/web-test", "/validation"):
            if not WEB_VALIDATION.exists():
                return self._json(404, {"error": "web validation UI unavailable"})
            return self._html(200, WEB_VALIDATION.read_text(encoding="utf-8"))
        if path == "/api/avatar.glb":
            if not AVATAR_GLB.is_file():return self._json(404,{"error":"private krishna.glb unavailable"})
            return self._binary(200,AVATAR_GLB.read_bytes(),"model/gltf-binary")
        if path == "/api/avatar360":
            body = avatar_360_bytes()
            if not body:
                return self._json(404, {"error": "avatar asset unavailable"})
            return self._binary(200, body, "image/webp")
        if path == "/api/attachments":
            chat_id=(query.get("chat_id") or [""])[0].strip()
            if not chat_id:return self._json(400,{"error":"chat_id is required"})
            return self._json(200,{"attachments":_attachments.list(chat_id)})
        if path == "/api/garuda/status":
            return self._json(200, orch.garuda_status())
        if path == "/api/gyan-bhandar/theory":
            project=(query.get("project") or ["KRISHNA"])[0].strip() or "KRISHNA"; topic=(query.get("topic") or [""])[0].strip()
            if not topic:return self._json(400,{"error":"topic is required"})
            try:return self._json(200,orch.gyan_theory(project,topic,25))
            except KeyError:return self._json(404,{"error":"project not registered"})
        if path == "/api/gyan-bhandar":
            project=(query.get("project") or ["KRISHNA"])[0].strip() or "KRISHNA"
            topic=(query.get("topic") or [None])[0]
            verified=str((query.get("verified") or ["0"])[0]).lower() in {"1","true","yes"}
            try:return self._json(200,{"agent":"Gyan-Bhandar","project":project,"learnings":orch.gyan_recall(project,topic,100,verified)})
            except KeyError:return self._json(404,{"error":"project not registered"})
        if path in ("/health", "/api/status"):
            return self._json(200, {
                "ok": True,
                "core": "ONLINE",
                "watcher": watcher.snapshot(),
                "resources": orch.governor.snapshot(),
                "pc_observer": pc_observer.snapshot(),
                "mobile_connection": mobile_link_state(),
                "uptime_seconds": int(time.time() - started),
            })
        if path == "/api/dashboard":
            return self._json(200, {
                "active": True,
                "core": "ONLINE",
                "watcher": watcher.snapshot(),
                "resources": orch.governor.snapshot(),
                "pc_observer": pc_observer.snapshot(),
                "neural": orch.neural_state(),
                "current_activity": activity["current_activity"],
                "updated": activity["updated"],
                "recent": activity["recent"],
                "mobile_connection": mobile_link_state(),
                "uptime_seconds": int(time.time() - started),
            })
        if path == "/api/mobile/connection":
            return self._json(200, mobile_link_state())
        if path == "/api/mobile/resume":
            device, token = self._device_auth()
            if not _pairing.verify(device, token):
                return self._json(401, {"error": "pairing required"})
            seq = int((query.get("after") or [0])[0])
            return self._json(200, {"ok": True, "events": _sessions.after(device, seq)})
        if path == "/api/capabilities":
            return self._json(200, {
                "operating_loop": [
                    "observe", "understand", "investigate", "research",
                    "plan", "act", "shadow_test", "verify", "review", "learn"
                ],
                "capabilities": [
                    "project_registry",
                    "repository_index",
                    "project_graph",
                    "evidence_engine",
                    "hypothesis_investigation",
                    "persistent_incident_memory",
                    "knowledge_ingestion",
                    "registered_action_registry",
                    "shadow_workspace",
                    "shadow_repair_pipeline",
                    "verification_gates",
                    "verification_review",
                    "resource_governor",
                    "privacy_aware_model_routing",
                    "chromium_ui_inspection",
                    "github_repository_research",
                    "goal_completion_evaluation",
                    "recovery_ladder",
                    "defensive_security_scan",
                    "watcher_transitions",
                    "neural_action_graph",
                    "pc_resource_observer",
                    "registered_project_change_observer",
                    "mobile_event_bridge",
                    "child_krishna_360_avatar",
                    "mobile_pc_remote_control",
                    "persistent_project_chats",
                    "windows_conversation_console",
                    "on_demand_skill_runtime",
                    "untrusted_content_boundary",
                    "specialist_permission_manifests",
                ],
                "mutating_actions_enabled": settings.allow_actions,
            })
        if path == "/api/projects":
            return self._json(200, {"projects": orch.projects.list()})
        if path == "/api/plugins":
            return self._json(200, {"plugins": _plugins.list()})
        if path == "/api/specialists":
            return self._json(200, _specialists.status())
        if path == "/api/skills":
            project = (query.get("project") or [None])[0]
            return self._json(200, orch.skill_status(project))
        if path == "/api/actions":
            project = (query.get("project") or [None])[0]
            return self._json(200, {"actions": orch.actions.list(project)})
        if path == "/api/resources":
            return self._json(200, orch.governor.snapshot())
        if path == "/api/tasks":
            project = (query.get("project") or [None])[0]
            limit_raw = (query.get("limit") or ["100"])[0]
            try:
                limit = max(1, min(int(limit_raw), 500))
            except (TypeError, ValueError):
                return self._json(400, {"error": "limit must be an integer"})
            tasks = orch.task_ledger.list_tasks(project=project, limit=limit)
            return self._json(200, {"tasks": tasks, "active": [t for t in tasks if t.get("status") in {"queued","running","verifying","waiting_approval"}]})
        if path in ("/api/core/neural-state", "/api/neural/state"):
            return self._json(200, orch.neural_state())
        if path == "/api/core/state":
            current = activity["current_activity"]
            return self._json(200, {
                "operator": {
                    "avatar_state": "FLUTE" if current == "Idle" else "WORKING",
                    "current": {"task": current},
                    "updated": activity["updated"],
                },
                "neural": orch.neural_state(),
                "pc_observer": pc_observer.snapshot(),
            })
        if path == "/api/chats":
            project = (query.get("project") or [None])[0]
            return self._json(200, {"chats": orch.chats(project)})
        if path == "/api/chat/history":
            chat_id = (query.get("chat_id") or [""])[0]
            if not chat_id:
                return self._json(400, {"error": "chat_id is required"})
            return self._json(200, {
                "chat_id": chat_id,
                "messages": orch.chat_messages(chat_id, 100),
            })
        if path == "/api/project-graph":
            return self._json(200, orch.graph.snapshot())
        if path == "/api/recovery/ladder":
            return self._json(200, {"steps": orch.recovery.ladder()})
        if path == "/api/incidents":
            project = (query.get("project") or [None])[0]
            return self._json(200, {"incidents": orch.memory.incidents(project, 50)})
        return self._json(404, {"error": "not found"})

    def do_POST(self):
        touch_mobile(self.headers.get("X-Krishna-Device"), self.path)
        try:
            data = self._body()
        except Exception as exc:
            return self._json(400, {"error": f"invalid json: {exc}"})

        if self.path == "/api/mobile/pair/request":
            device = str(data.get("device_id", "")).strip()
            if not device:
                return self._json(400, {"error": "device_id required"})
            return self._json(200, _pairing.request(device, str(data.get("name", "KRISHNA Mobile"))[:128]))

        if self.path == "/api/mobile/pair/approve":
            if self.client_address[0] not in ("127.0.0.1", "::1"):
                return self._json(403, {"error": "approval must be performed on KRISHNA PC"})
            try:
                return self._json(200, _pairing.approve(str(data.get("request_id", ""))))
            except PermissionError as exc:
                return self._json(400, {"error": str(exc)})

        if self.path in ("/api/core/event", "/api/neural/event"):
            if str(data.get("source", "")).lower() == "mobile":
                touch_mobile(self.headers.get("X-Krishna-Device") or "android-primary", self.path)
            source = str(data.get("source", "unknown")).strip() or "unknown"
            kind = str(data.get("kind", "event")).strip() or "event"
            detail = str(data.get("detail", ""))
            severity = str(data.get("severity", "info"))
            project = str(data.get("project", "system"))
            return self._json(200, orch.handle_event(
                source, kind, detail, severity=severity, project=project,
                payload=data.get("payload") or {},
            ))

        if self.path in ("/api/mobile-log",):
            touch_mobile(self.headers.get("X-Krishna-Device") or "android-primary", self.path)
            event = str(data.get("event", ""))
            return self._json(200, orch.handle_event(
                "mobile", "mobile_log", event, severity="info", project="system",
            ))

        if self.path == "/api/mobile/control":
            action = str(data.get("action", "")).strip().lower()
            project = str(data.get("project", "general")).strip() or "general"
            payload = data.get("payload") or {}
            safe_actions = {
                "status", "projects", "chats", "index", "investigate",
                "inspect_ui", "research_github", "incidents", "engines",
            }
            if action not in safe_actions:
                return self._json(403, {
                    "error": "mobile action is not in the approved control set",
                    "allowed": sorted(safe_actions),
                })
            try:
                if action == "status":
                    return self._json(200, {
                        "ok": True,
                        "core": "ONLINE",
                        "watcher": watcher.snapshot(),
                        "resources": orch.governor.snapshot(),
                        "pc_observer": pc_observer.snapshot(),
                        "mobile_connection": mobile_link_state(),
                    })
                if action == "projects":
                    return self._json(200, {"projects": orch.projects.list()})
                if action == "chats":
                    return self._json(200, {"chats": orch.chats(project)})
                if action == "index":
                    return self._json(200, orch.index_project(project))
                if action == "investigate":
                    symptom = str(payload.get("symptom", "")).strip()
                    if not symptom:
                        return self._json(400, {"error": "symptom is required"})
                    return self._json(200, orch.investigate(symptom, project, payload.get("components") or []))
                if action == "inspect_ui":
                    url = str(payload.get("url", "")).strip()
                    if not url:
                        return self._json(400, {"error": "url is required"})
                    return self._json(200, orch.inspect_ui(
                        project, url,
                        actions=payload.get("actions") or [],
                        screenshot_path=payload.get("screenshot_path"),
                    ))
                if action == "research_github":
                    query = str(payload.get("query", "")).strip()
                    if not query:
                        return self._json(400, {"error": "query is required"})
                    return self._json(200, orch.research_github(project, query, int(payload.get("limit", 10))))
                if action == "incidents":
                    return self._json(200, {"incidents": orch.memory.incidents(project, 50)})
                if action == "engines":
                    return self._json(200, {
                        "capabilities": [
                            "project_registry","repository_index","project_graph",
                            "evidence_engine","hypothesis_investigation",
                            "persistent_incident_memory","knowledge_ingestion",
                            "registered_action_registry","shadow_workspace",
                            "shadow_repair_pipeline","verification_gates",
                            "verification_review","resource_governor",
                            "privacy_aware_model_routing","chromium_ui_inspection",
                            "github_repository_research","goal_completion_evaluation",
                            "recovery_ladder","defensive_security_scan",
                            "watcher_transitions","neural_action_graph",
                            "pc_resource_observer","registered_project_change_observer",
                            "mobile_event_bridge","persistent_project_chats",
                            "windows_conversation_console","child_krishna_360_avatar",
                            "mobile_pc_remote_control",
                            "on_demand_skill_runtime","untrusted_content_boundary",
                            "specialist_permission_manifests",
                        ]
                    })
            except KeyError:
                return self._json(404, {"error": "project not registered"})
            except (ValueError, RuntimeError) as exc:
                return self._json(400, {"error": str(exc)})
            except Exception as exc:
                return self._json(500, {"error": str(exc)})

        if self.path in ("/v1/chat", "/api/core/chat"):
            if str(data.get("source", "")).lower() == "mobile":
                touch_mobile(self.headers.get("X-Krishna-Device") or "android-primary", self.path)
            msg = data.get("message", "")
            # KRISHNA is the only public identity/mode. Legacy internal mode values are
            # accepted for compatibility but are not required by clients.
            requested_mode = str(data.get("mode", "chat")).strip().lower()
            if requested_mode not in ("chat", "karma", "vishwakarma"):
                return self._json(400, {"error": "invalid legacy mode"})
            mode = "chat"
            mark("REQUEST RECEIVED", f"{mode}: {msg[:110]}")
            try:
                mark("KRISHNA WORKING", "Processing request")
                project = data.get("project", "general")
                # KRISHNA selects internal capabilities automatically. Clients never
                # need to choose Sudarshan/Karma/Vishwakarma manually.
                if orch._looks_like_work_request(msg):
                    out = orch.handle_managed_request(msg, project, data.get("source", "pc"), data.get("chat_id"))
                else:
                    out = orch.handle(msg, project, data.get("source", "pc"), data.get("chat_id"))
                out["mode"] = "chat"
                out["identity"] = "KRISHNA"
                out.setdefault("capability", "conversation")
                mark("REQUEST COMPLETE", "Response generated by Core")
                activity["current_activity"] = "Idle"
                orch.handle_event(
                    data.get("source", "pc"),
                    "task_completed",
                    "KRISHNA response generated and returned",
                    severity="notice",
                    project=data.get("project", "general"),
                    payload={"task_id": out.get("task_id")},
                )
                if str(data.get("source", "")).lower() == "mobile":
                    device, token = self._device_auth()
                    if _pairing.verify(device, token):
                        _sessions.publish(device, "task.completed", {
                            "project": data.get("project", "general"),
                            "chat_id": out.get("chat_id") or data.get("chat_id"),
                            "task_id": out.get("task_id"),
                            "summary": (out.get("reply") or out.get("text") or "KRISHNA completed the task")[:240],
                        })
                return self._json(200, out)
            except Exception as exc:
                mark("ERROR", str(exc)[:160])
                activity["current_activity"] = "Error"
                return self._json(500, {"error": str(exc)})

        if self.path == "/api/specialists/index":
            try:
                return self._json(200, _specialists.index(data.get("source_root") or None))
            except ValueError as exc:
                return self._json(400, {"error": str(exc)})

        if self.path == "/api/specialists/select":
            task = str(data.get("task", "")).strip()
            if not task:
                return self._json(400, {"error": "task is required"})
            return self._json(200, {"selected": _specialists.select(task, int(data.get("limit", 5)))})

        if self.path == "/api/specialists/context":
            try:
                return self._json(200, _specialists.context(str(data.get("id", ""))))
            except KeyError:
                return self._json(404, {"error": "specialist not found"})
            except PermissionError as exc:
                return self._json(403, {"error": str(exc)})

        if self.path == "/api/plugins/add":
            try:
                return self._json(200, _plugins.add(data))
            except ValueError as exc:
                return self._json(400, {"error": str(exc)})

        if self.path == "/api/plugins/enable":
            try:
                return self._json(200, _plugins.set_enabled(str(data.get("id", "")).strip(), bool(data.get("enabled", True))))
            except KeyError:
                return self._json(404, {"error": "plugin not found"})

        if self.path == "/api/plugins/remove":
            try:
                return self._json(200, {"removed": _plugins.remove(str(data.get("id", "")).strip())})
            except PermissionError as exc:
                return self._json(403, {"error": str(exc)})

        if self.path == "/api/chats/create":
            project = str(data.get("project", "general")).strip() or "general"
            title = str(data.get("title", "New chat")).strip() or "New chat"
            try:
                return self._json(200, orch.create_chat(project, title))
            except KeyError:
                return self._json(404, {"error": "project not registered"})

        if self.path == "/api/chats/move":
            chat_id = str(data.get("chat_id", "")).strip()
            project = str(data.get("project", "")).strip()
            if not chat_id or not project:
                return self._json(400, {"error": "chat_id and project are required"})
            try:
                return self._json(200, orch.move_chat(chat_id, project))
            except KeyError as exc:
                return self._json(404, {"error": str(exc)})
            except ValueError as exc:
                return self._json(400, {"error": str(exc)})

        if self.path == "/api/chats/rename":
            chat_id = str(data.get("chat_id", "")).strip()
            title = str(data.get("title", "")).strip()
            if not chat_id or not title:
                return self._json(400, {"error": "chat_id and title are required"})
            try:
                return self._json(200, orch.rename_chat(chat_id, title))
            except KeyError as exc:
                return self._json(404, {"error": str(exc)})
            except ValueError as exc:
                return self._json(400, {"error": str(exc)})

        if self.path == "/api/projects/register":
            try:
                out = orch.register_project(
                    name=str(data.get("name", "")).strip(),
                    root=str(data.get("root", "")).strip(),
                    privacy=str(data.get("privacy", "local_only")),
                    allowed_actions=data.get("allowed_actions") or [],
                    verification_checks=data.get("verification_checks") or [],
                    metadata=data.get("metadata") or {},
                )
                return self._json(200, out)
            except (ValueError, TypeError) as exc:
                return self._json(400, {"error": str(exc)})

        if self.path == "/api/projects/unregister":
            name = str(data.get("name", "")).strip()
            try:
                return self._json(200, orch.unregister_project(name))
            except KeyError:
                return self._json(404, {"error": "project not registered"})
            except PermissionError as exc:
                return self._json(403, {"error": str(exc)})
            except ValueError as exc:
                return self._json(400, {"error": str(exc)})

        if self.path == "/api/e2e/register":
            if self.client_address[0] not in ("127.0.0.1", "::1"):
                return self._json(403, {"error": "E2E harness registration must be performed on KRISHNA PC"})
            project = str(data.get("project", "")).strip()
            if not project:
                return self._json(400, {"error": "project is required"})
            try:
                return self._json(200, orch.register_e2e_test_harness(project))
            except KeyError:
                return self._json(404, {"error": "project not registered"})
            except PermissionError as exc:
                return self._json(403, {"error": str(exc)})
            except (OSError, ValueError) as exc:
                return self._json(400, {"error": str(exc)})

        if self.path == "/api/projects/index":
            project = str(data.get("project", "")).strip()
            if not project:
                return self._json(400, {"error": "project is required"})
            try:
                return self._json(200, orch.index_project(project))
            except KeyError:
                return self._json(404, {"error": "project not registered"})

        if self.path == "/api/investigate":
            symptom = str(data.get("symptom", "")).strip()
            if not symptom:
                return self._json(400, {"error": "symptom is required"})
            project = str(data.get("project", "general"))
            components = data.get("components") or []
            mark("INVESTIGATING", symptom[:120])
            try:
                out = orch.investigate(symptom, project, components)
                mark("EVIDENCE COLLECTED", out["investigation_id"])
                activity["current_activity"] = "Idle"
                return self._json(200, out)
            except Exception as exc:
                mark("INVESTIGATION ERROR", str(exc)[:160])
                return self._json(500, {"error": str(exc)})

        if self.path == "/api/attachments":
            chat_id=str(data.get("chat_id") or "").strip()
            if not chat_id or not orch.memory.chat(chat_id):return self._json(404,{"error":"chat not found"})
            try:
                item=_attachments.save(chat_id,data.get("name"),data.get("data_b64"),data.get("content_type"))
                orch.memory.add_chat_message(chat_id,"tool","Attachment added",{"attachment":item})
                return self._json(201,item)
            except (ValueError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if self.path == "/api/plugins/execute":
            try:
                return self._json(200,_plugin_executor.execute(str(data.get("plugin_id") or ""),str(data.get("project") or "KRISHNA"),str(data.get("operation") or "get"),data.get("payload") or {},data.get("auth_env")))
            except KeyError:return self._json(404,{"error":"plugin not found"})
            except (ValueError,PermissionError) as exc:return self._json(403 if isinstance(exc,PermissionError) else 400,{"error":str(exc)})
            except Exception as exc:return self._json(502,{"error":f"plugin request failed: {type(exc).__name__}: {exc}"})

        if self.path == "/api/gyan-bhandar/store":
            project=str(data.get("project") or "KRISHNA").strip(); topic=str(data.get("topic") or "").strip(); lesson=str(data.get("lesson") or "").strip()
            if not topic or not lesson:return self._json(400,{"error":"topic and lesson are required"})
            try:return self._json(201,orch.gyan_store(project,topic,lesson,data.get("evidence") or [],float(data.get("confidence") or 0),str(data.get("source") or "sudarshan"),bool(data.get("verified",False))))
            except KeyError:return self._json(404,{"error":"project not registered"})
            except (ValueError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if self.path == "/api/gyan-bhandar/strengthen":
            project=str(data.get("project") or "KRISHNA").strip(); topic=str(data.get("topic") or "").strip()
            if not topic:return self._json(400,{"error":"topic is required"})
            try:return self._json(200,orch.gyan_strengthen(project,topic,bool(data.get("use_garuda",True)),int(data.get("limit") or 10)))
            except KeyError:return self._json(404,{"error":"project not registered"})
            except (ValueError,RuntimeError) as exc:return self._json(400,{"error":str(exc)})

        if self.path == "/api/garuda/scout":
            project=str(data.get("project") or "KRISHNA").strip()
            goal=str(data.get("goal") or "").strip()
            if not goal:return self._json(400,{"error":"goal is required"})
            try:return self._json(200,orch.garuda_scout(project,goal,int(data.get("limit") or 10)))
            except KeyError:return self._json(404,{"error":"project not registered"})
            except (ValueError,RuntimeError) as exc:return self._json(400,{"error":str(exc)})

        if self.path == "/api/development/git/status":
            project=str(data.get("project","")).strip()
            if not project:return self._json(400,{"error":"project is required"})
            try:return self._json(200,orch.development_git_snapshot(project))
            except KeyError:return self._json(404,{"error":"project not registered"})

        if self.path == "/api/development/git/commit":
            project=str(data.get("project","")).strip()
            try:return self._json(200,orch.development_commit(project,str(data.get("message","KRISHNA verified change")),data.get("files") or [],bool(data.get("approved",False))))
            except KeyError:return self._json(404,{"error":"project not registered"})
            except (ValueError,PermissionError) as exc:return self._json(403 if isinstance(exc,PermissionError) else 400,{"error":str(exc)})

        if self.path == "/api/development/git/push":
            project=str(data.get("project","")).strip()
            try:return self._json(200,orch.development_push(project,bool(data.get("approved",False))))
            except KeyError:return self._json(404,{"error":"project not registered"})
            except PermissionError as exc:return self._json(403,{"error":str(exc)})

        if self.path == "/api/development/sync":
            project=str(data.get("project","")).strip()
            if not project:return self._json(400,{"error":"project is required"})
            try:return self._json(200,orch.development_sync(project))
            except KeyError:return self._json(404,{"error":"project not registered"})

        if self.path == "/api/development/stage":
            project=str(data.get("project","")).strip(); files=data.get("files") or []
            if not project or not isinstance(files,list):return self._json(400,{"error":"project and files are required"})
            try:return self._json(200,orch.development_stage(project,files))
            except KeyError:return self._json(404,{"error":"project not registered"})
            except (ValueError,OSError) as exc:return self._json(400,{"error":str(exc)})

        if self.path == "/api/development/verify":
            project=str(data.get("project","")).strip(); candidate=str(data.get("candidate_root","")).strip()
            if not project or not candidate:return self._json(400,{"error":"project and candidate_root are required"})
            try:return self._json(200,orch.development_verify(project,candidate,data.get("checks") or [],data.get("frontend_url"),data.get("browser_actions") or [],data.get("api_expectations") or [],data.get("screenshot_path") or None))
            except KeyError:return self._json(404,{"error":"project not registered"})
            except (ValueError,OSError,RuntimeError) as exc:return self._json(400,{"error":str(exc)})

        if self.path == "/api/work/run":
            project = str(data.get("project", "")).strip()
            goal = str(data.get("goal", "")).strip()
            action = str(data.get("action", "")).strip() or None
            if not project or not goal:
                return self._json(400, {"error": "project and goal are required"})
            try:
                out = orch.run_managed_goal(
                    project, goal,
                    action_name=action,
                    components=data.get("components") or [],
                    approved=bool(data.get("approved", False)),
                )
                return self._json(200, out)
            except KeyError as exc:
                return self._json(404, {"error": str(exc)})
            except PermissionError as exc:
                return self._json(403, {"error": str(exc)})
            except RuntimeError as exc:
                return self._json(409, {"error": str(exc)})

        if self.path == "/api/work/promotion/prepare":
            project=str(data.get("project","")).strip()
            candidate=str(data.get("candidate_root","")).strip()
            if not project or not candidate: return self._json(400,{"error":"project and candidate_root are required"})
            try: return self._json(200,orch.prepare_promotion(project,candidate,data.get("task_id")))
            except KeyError as exc: return self._json(404,{"error":str(exc)})
            except ValueError as exc: return self._json(400,{"error":str(exc)})

        if self.path == "/api/work/promotion/apply":
            token=str(data.get("promotion_token","")).strip()
            if not token: return self._json(400,{"error":"promotion_token is required"})
            try: return self._json(200,orch.promote_candidate(token,approved=bool(data.get("approved",False))))
            except KeyError as exc: return self._json(404,{"error":str(exc)})
            except PermissionError as exc: return self._json(403,{"error":str(exc)})
            except (ValueError,RuntimeError) as exc: return self._json(409,{"error":str(exc)})

        if self.path == "/api/repair/shadow":
            project = str(data.get("project", "")).strip()
            symptom = str(data.get("symptom", "")).strip()
            action = str(data.get("action", "")).strip()
            if not project or not symptom or not action:
                return self._json(400, {"error": "project, symptom and action are required"})
            mark("SHADOW REPAIR", f"{project}: {symptom[:80]}")
            try:
                out = orch.run_shadow_repair(project, symptom, action, data.get("components") or [])
                mark("SHADOW VERIFIED" if out["promotable"] else "SHADOW REJECTED", out["repair_id"])
                if out.get("promotable"):
                    orch.handle_event(
                        "pc", "repair_verified", f"{project}: {out['repair_id']}",
                        severity="notice", project=project,
                        payload={"repair_id": out["repair_id"]},
                    )
                activity["current_activity"] = "Idle"
                return self._json(200, out)
            except KeyError as exc:
                return self._json(404, {"error": str(exc)})
            except PermissionError as exc:
                return self._json(403, {"error": str(exc)})
            except RuntimeError as exc:
                return self._json(409, {"error": str(exc)})

        if self.path == "/api/browser/inspect":
            project = str(data.get("project", "general"))
            url = str(data.get("url", "")).strip()
            if not url:
                return self._json(400, {"error": "url is required"})
            try:
                out = orch.inspect_ui(
                    project,
                    url,
                    actions=data.get("actions") or [],
                    screenshot_path=data.get("screenshot_path"),
                )
                return self._json(200, out)
            except (ValueError, RuntimeError) as exc:
                return self._json(400, {"error": str(exc)})
            except Exception as exc:
                return self._json(500, {"error": str(exc)})

        if self.path == "/api/research/github":
            project = str(data.get("project", "general"))
            query = str(data.get("query", "")).strip()
            if not query:
                return self._json(400, {"error": "query is required"})
            try:
                out = orch.research_github(project, query, int(data.get("limit", 10)))
                return self._json(200, out)
            except (ValueError, RuntimeError) as exc:
                return self._json(400, {"error": str(exc)})
            except Exception as exc:
                return self._json(500, {"error": str(exc)})

        if self.path == "/api/goal/evaluate":
            project = str(data.get("project", "general"))
            goal = str(data.get("goal", "")).strip()
            checks = data.get("checks") or []
            if not goal:
                return self._json(400, {"error": "goal is required"})
            return self._json(200, orch.evaluate_goal(project, goal, checks))

        if self.path == "/api/knowledge/ingest":
            project = str(data.get("project", "general"))
            source = str(data.get("source", "manual"))
            text = str(data.get("text", ""))
            if not text.strip():
                return self._json(400, {"error": "text is required"})
            result = orch.ingest_knowledge(project, source, text, data.get("metadata"))
            return self._json(200, result)

        if self.path == "/api/project-graph/node":
            name = str(data.get("name", "")).strip()
            if not name:
                return self._json(400, {"error": "name is required"})
            orch.graph.upsert_node(name, str(data.get("kind", "component")), data.get("metadata") or {})
            return self._json(200, {"ok": True})

        if self.path == "/api/project-graph/link":
            source = str(data.get("source", "")).strip()
            target = str(data.get("target", "")).strip()
            if not source or not target:
                return self._json(400, {"error": "source and target are required"})
            orch.graph.link(source, target, str(data.get("relation", "depends_on")))
            return self._json(200, {"ok": True})

        if self.path == "/api/security/scan-text":
            path = str(data.get("path", "submitted-text"))
            text = str(data.get("text", ""))
            return self._json(200, {
                "authorized_defensive_scan": True,
                "findings": orch.security.scan_text(path, text),
            })

        if self.path == "/api/recovery/execute":
            step = str(data.get("step", "")).strip()
            if not step:
                return self._json(400, {"error": "step is required"})
            try:
                return self._json(200, orch.recovery.execute(step, data.get("payload") or {}))
            except KeyError:
                return self._json(404, {"error": "unknown recovery step"})

        return self._json(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    print(f"KRISHNA Core: http://127.0.0.1:{settings.port}/dashboard")
    ThreadingHTTPServer((settings.host, settings.port), Handler).serve_forever()
