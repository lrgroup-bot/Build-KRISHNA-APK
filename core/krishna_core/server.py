from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import json
from .config import settings
from .orchestrator import Orchestrator
from .watcher import Watcher

orch=Orchestrator(); watcher=Watcher(); watcher.start()

class Handler(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        b=json.dumps(obj).encode(); self.send_response(code); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if self.path=="/health": return self._json(200,{"ok":True,"watcher":watcher.state})
        return self._json(404,{"error":"not found"})
    def do_POST(self):
        n=int(self.headers.get("Content-Length","0")); data=json.loads(self.rfile.read(n) or b"{}")
        if self.path in ("/v1/chat","/api/core/chat"):
            try: return self._json(200,orch.handle(data.get("message",""),data.get("project","general")))
            except Exception as e: return self._json(500,{"error":str(e)})
        return self._json(404,{"error":"not found"})

if __name__=="__main__":
    ThreadingHTTPServer((settings.host,settings.port),Handler).serve_forever()
