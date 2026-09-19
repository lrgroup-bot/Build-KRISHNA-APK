from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import json, time
from pathlib import Path
from .config import settings
from .orchestrator import Orchestrator
from .watcher import Watcher

orch = Orchestrator()
started = time.time()
activity = {"current_activity": "Idle", "updated": time.strftime("%Y-%m-%d %H:%M:%S"), "recent": []}
DASHBOARD = (Path(__file__).resolve().parents[1] / "dashboard.html")

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

watcher = Watcher(on_transition=on_transition)
watcher.start()

class Handler(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

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
        if n > 8 * 1024 * 1024:
            raise ValueError("request body exceeds 8 MB")
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        if self.path in ("/", "/dashboard"):
            return self._html(200, DASHBOARD.read_text(encoding="utf-8"))
        if self.path == "/health":
            return self._json(200, {
                "ok": True,
                "watcher": watcher.snapshot(),
                "uptime_seconds": int(time.time() - started),
            })
        if self.path == "/api/dashboard":
            return self._json(200, {
                "active": True,
                "core": "ONLINE",
                "watcher": watcher.snapshot(),
                "current_activity": activity["current_activity"],
                "updated": activity["updated"],
                "recent": activity["recent"],
                "uptime_seconds": int(time.time() - started),
            })
        if self.path == "/api/capabilities":
            return self._json(200, {
                "operating_loop": [
                    "observe", "understand", "investigate", "research", "plan",
                    "change_gate", "shadow_execute", "test", "verify", "learn"
                ],
                "capabilities": [
                    "project_graph",
                    "evidence_engine",
                    "hypothesis_investigation",
                    "persistent_incident_memory",
                    "knowledge_ingestion",
                    "verification_gates",
                    "recovery_ladder",
                    "defensive_security_scan",
                    "watcher_transitions",
                    "local_cloud_model_routing",
                    "vision_local_enrolled_identity",
                    "mythos_engineering_stack",
                    "code_intelligence_adapters",
                    "hard_change_gate",
                    "shadow_workspaces",
                    "linear_engineering_worker",
                    "computer_use_adapter",
                    "extension_bus",
                ],
                "mutating_actions_enabled": settings.allow_actions,
                "vision": orch.vision.status(),
                "engineering": orch.engineering.status(),
            })
        if self.path == "/api/engineering/status":
            return self._json(200, orch.engineering.status())
        if self.path == "/api/engineering/operator/status":
            return self._json(200, orch.engineering.operator.status())
        if self.path == "/api/vision/status":
            return self._json(200, orch.vision.status())
        if self.path == "/api/project-graph":
            return self._json(200, orch.graph.snapshot())
        if self.path == "/api/recovery/ladder":
            return self._json(200, {"steps": orch.recovery.ladder()})
        if self.path.startswith("/api/incidents"):
            project = None
            if "?project=" in self.path:
                project = self.path.split("?project=", 1)[1].split("&", 1)[0]
            return self._json(200, {"incidents": orch.memory.incidents(project, 50)})
        return self._json(404, {"error": "not found"})

    def do_POST(self):
        try:
            data = self._body()
        except Exception as exc:
            return self._json(400, {"error": f"invalid request: {exc}"})

        if self.path in ("/v1/chat", "/api/core/chat"):
            msg = data.get("message", "")
            mark("REQUEST RECEIVED", msg[:120])
            try:
                mark("KRISHNA WORKING", "Processing request")
                out = orch.handle(msg, data.get("project", "general"))
                mark("REQUEST COMPLETE", "Response generated by Core")
                activity["current_activity"] = "Idle"
                return self._json(200, out)
            except Exception as exc:
                mark("ERROR", str(exc)[:160])
                activity["current_activity"] = "Error"
                return self._json(500, {"error": str(exc)})

        if self.path == "/api/engineering/recon":
            project = str(data.get("project", "general"))
            project_path = str(data.get("project_path", "")).strip()
            symptom = str(data.get("symptom", "")).strip()
            if not project_path or not symptom:
                return self._json(400, {"error": "project_path and symptom are required"})
            mark("ENGINEERING RECON", symptom[:120])
            try:
                out = orch.engineering_recon(project, project_path, symptom, data.get("components") or [])
                activity["current_activity"] = "Idle"
                return self._json(200, out)
            except Exception as exc:
                mark("ENGINEERING RECON ERROR", str(exc)[:160])
                return self._json(500, {"error": str(exc)})

        if self.path == "/api/engineering/change-gate":
            path = str(data.get("path", "")).strip()
            if not path:
                return self._json(400, {"error": "path is required"})
            try:
                out = orch.engineering.assess_change(
                    path=path,
                    expected_hash=data.get("expected_hash"),
                    caller_count=int(data.get("caller_count", 0)),
                    changed_lines=int(data.get("changed_lines", 0)),
                    tests_present=bool(data.get("tests_present", False)),
                    external_risk=data.get("external_risk"),
                    explicit_confirmation=bool(data.get("explicit_confirmation", False)),
                )
                return self._json(200, out)
            except Exception as exc:
                return self._json(400, {"error": str(exc)})

        if self.path == "/api/engineering/shadow-plan":
            project = str(data.get("project", "general"))
            source = str(data.get("source", "")).strip()
            actions = data.get("actions") or []
            if not source or not isinstance(actions, list):
                return self._json(400, {"error": "source and actions are required"})
            try:
                out = orch.engineering.run_shadow_plan(project, source, actions)
                return self._json(200, out)
            except Exception as exc:
                return self._json(400, {"error": str(exc)})

        if self.path == "/api/engineering/operator/diagnostic":
            return self._json(200, orch.engineering.operator.diagnostic())

        if self.path == "/api/vision/enroll":
            mark("VISION ENROLL", str(data.get("name", ""))[:80])
            try:
                out = orch.vision.enroll(
                    name=data.get("name", ""),
                    image_base64=data.get("image_base64", ""),
                    consent=bool(data.get("consent", False)),
                    device=str(data.get("device", "unknown")),
                )
                mark("VISION ENROLLED", out.get("subject", ""))
                activity["current_activity"] = "Idle"
                return self._json(200, out)
            except ValueError as exc:
                mark("VISION ENROLL REJECTED", str(exc)[:120])
                return self._json(400, {"error": str(exc)})
            except Exception as exc:
                mark("VISION ENROLL ERROR", str(exc)[:120])
                return self._json(503, {"error": str(exc)})

        if self.path == "/api/vision/recognize":
            mark("VISION SCAN", "Comparing with local enrolled gallery")
            try:
                out = orch.vision.recognize(
                    image_base64=data.get("image_base64", ""),
                    device=str(data.get("device", "unknown")),
                )
                mark("VISION RESULT", out.get("state", "UNKNOWN"))
                activity["current_activity"] = "Idle"
                return self._json(200, out)
            except ValueError as exc:
                mark("VISION SCAN REJECTED", str(exc)[:120])
                return self._json(400, {"error": str(exc)})
            except Exception as exc:
                mark("VISION SCAN ERROR", str(exc)[:120])
                return self._json(503, {"error": str(exc)})

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
