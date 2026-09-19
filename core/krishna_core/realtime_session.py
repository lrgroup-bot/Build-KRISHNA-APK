"""Durable realtime session/event log used by mobile transports."""
from __future__ import annotations
from pathlib import Path
import json, threading, time, uuid

class RealtimeSessionStore:
    def __init__(self,state_dir):
        self.root=Path(state_dir)/"realtime"; self.root.mkdir(parents=True,exist_ok=True); self.lock=threading.RLock()
    def _path(self,device_id): return self.root/(device_id.replace("/","_").replace("\\","_")+".json")
    def _load(self,d):
        try:return json.loads(self._path(d).read_text("utf-8"))
        except Exception:return {"next_seq":1,"events":[],"seen":{}}
    def _save(self,d,v):
        p=self._path(d); t=p.with_suffix(".tmp"); t.write_text(json.dumps(v,separators=(",",":")),"utf-8"); t.replace(p)
    def publish(self,device_id,event_type,payload,idempotency_key=None):
        with self.lock:
            s=self._load(device_id)
            if idempotency_key and idempotency_key in s["seen"]: return s["seen"][idempotency_key]
            e={"id":str(uuid.uuid4()),"seq":s["next_seq"],"type":event_type,"payload":payload,"ts":int(time.time())}
            s["next_seq"]+=1; s["events"].append(e); s["events"]=s["events"][-500:]
            if idempotency_key: s["seen"][idempotency_key]=e; s["seen"]=dict(list(s["seen"].items())[-500:])
            self._save(device_id,s); return e
    def after(self,device_id,seq=0): return [e for e in self._load(device_id)["events"] if e["seq"]>int(seq)]
