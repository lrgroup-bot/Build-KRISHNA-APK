"""Local device-pairing store for KRISHNA PC <-> mobile trust."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib, json, secrets, time

@dataclass
class PendingPair:
    request_id:str; device_id:str; name:str; created_at:int; expires_at:int

class DevicePairingStore:
    def __init__(self,state_dir:str|Path,ttl:int=300):
        self.root=Path(state_dir)/"pairing"; self.root.mkdir(parents=True,exist_ok=True)
        self.pending_file=self.root/"pending.json"; self.paired_file=self.root/"paired.json"; self.ttl=ttl
    def _load(self,p):
        try:return json.loads(p.read_text("utf-8"))
        except Exception:return {}
    def _save(self,p,v):
        tmp=p.with_suffix(".tmp"); tmp.write_text(json.dumps(v,indent=2),"utf-8"); tmp.replace(p)
    def request(self,device_id:str,name:str)->dict:
        now=int(time.time()); pending=self._load(self.pending_file)
        pending={k:v for k,v in pending.items() if v.get("expires_at",0)>now}
        for v in pending.values():
            if v["device_id"]==device_id: self._save(self.pending_file,pending); return v
        r=asdict(PendingPair(secrets.token_urlsafe(18),device_id,name,now,now+self.ttl))
        pending[r["request_id"]]=r; self._save(self.pending_file,pending); return r
    def approve(self,request_id:str)->dict:
        pending=self._load(self.pending_file); r=pending.pop(request_id,None)
        if not r or r["expires_at"]<=int(time.time()): raise PermissionError("pairing request missing or expired")
        token=secrets.token_urlsafe(48); paired=self._load(self.paired_file)
        paired[r["device_id"]]={"name":r["name"],"token_sha256":hashlib.sha256(token.encode()).hexdigest(),"paired_at":int(time.time())}
        self._save(self.pending_file,pending); self._save(self.paired_file,paired)
        return {"device_id":r["device_id"],"token":token}
    def verify(self,device_id:str,token:str)->bool:
        v=self._load(self.paired_file).get(device_id)
        return bool(v) and secrets.compare_digest(v["token_sha256"],hashlib.sha256(token.encode()).hexdigest())
    def revoke(self,device_id:str):
        paired=self._load(self.paired_file); paired.pop(device_id,None); self._save(self.paired_file,paired)
