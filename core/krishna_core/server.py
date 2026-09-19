from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import json, time
from pathlib import Path
from .config import settings
from .orchestrator import Orchestrator
from .watcher import Watcher

orch=Orchestrator(); watcher=Watcher(); watcher.start()
started=time.time()
activity={"current_activity":"Idle","updated":time.strftime("%Y-%m-%d %H:%M:%S"),"recent":[]}
DASHBOARD=(Path(__file__).resolve().parents[1]/"dashboard.html")

def mark(event, detail=""):
    now=time.strftime("%H:%M:%S")
    activity["current_activity"]=detail or event
    activity["updated"]=time.strftime("%Y-%m-%d %H:%M:%S")
    activity["recent"].insert(0,{"time":now,"event":event+((": "+detail) if detail else "")})
    del activity["recent"][30:]

class Handler(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        b=json.dumps(obj).encode(); self.send_response(code); self.send_header("Content-Type","application/json"); self.send_header("Cache-Control","no-store"); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
    def _html(self, code, text):
        b=text.encode(); self.send_response(code); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Cache-Control","no-store"); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if self.path in ("/","/dashboard"): return self._html(200,DASHBOARD.read_text(encoding="utf-8"))
        if self.path=="/health": return self._json(200,{"ok":True,"watcher":watcher.state,"uptime_seconds":int(time.time()-started)})
        if self.path=="/api/dashboard":
            ws=watcher.state
            return self._json(200,{"active":True,"core":"ONLINE","watcher":str(ws),"current_activity":activity["current_activity"],"updated":activity["updated"],"recent":activity["recent"],"uptime_seconds":int(time.time()-started)})
        return self._json(404,{"error":"not found"})
    def do_POST(self):
        n=int(self.headers.get("Content-Length","0")); data=json.loads(self.rfile.read(n) or b"{}")
        if self.path in ("/v1/chat","/api/core/chat"):
            msg=data.get("message",""); mark("REQUEST RECEIVED",msg[:120])
            try:
                mark("KRISHNA WORKING","Processing request")
                out=orch.handle(msg,data.get("project","general"))
                mark("REQUEST COMPLETE","Response verified by Core")
                activity["current_activity"]="Idle"
                return self._json(200,out)
            except Exception as e:
                mark("ERROR",str(e)[:160]); activity["current_activity"]="Error"; return self._json(500,{"error":str(e)})
        return self._json(404,{"error":"not found"})
    def log_message(self, fmt, *args): pass

if __name__=="__main__":
    print(f"KRISHNA Core: http://127.0.0.1:{settings.port}/dashboard")
    ThreadingHTTPServer((settings.host,settings.port),Handler).serve_forever()
