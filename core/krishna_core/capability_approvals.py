from __future__ import annotations
import json,sqlite3,time
from threading import RLock
class CapabilityApprovals:
 def __init__(self,path):
  self.db=sqlite3.connect(path,check_same_thread=False);self.lock=RLock()
  with self.lock:self.db.execute("CREATE TABLE IF NOT EXISTS device_caps(device_id TEXT PRIMARY KEY,caps TEXT NOT NULL,updated_at REAL NOT NULL)");self.db.commit()
 def approved(self,device_id):
  with self.lock:r=self.db.execute("SELECT caps FROM device_caps WHERE device_id=?",(device_id,)).fetchone()
  return set(json.loads(r[0])) if r else set()
 def approve(self,device_id,caps):
  caps=sorted(set(str(x) for x in caps))
  with self.lock:self.db.execute("INSERT INTO device_caps VALUES(?,?,?) ON CONFLICT(device_id) DO UPDATE SET caps=excluded.caps,updated_at=excluded.updated_at",(device_id,json.dumps(caps),time.time()));self.db.commit()
  return {"device_id":device_id,"capabilities":caps}
 def require(self,device_id,cap):
  if cap not in self.approved(device_id):raise PermissionError("device capability not approved: "+cap)
