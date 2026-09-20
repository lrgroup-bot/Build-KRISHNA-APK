from __future__ import annotations
import json,sqlite3,time,uuid
from threading import RLock

class CommitmentLedger:
    """Durable ledger of decisions/promises so KRISHNA can resume unfinished work after restarts."""
    OPEN={"decided","planned","in_progress","blocked","waiting_approval"}
    DONE={"completed","cancelled","superseded"}
    def __init__(self,path):
        self.db=sqlite3.connect(path,check_same_thread=False); self.lock=RLock()
        with self.lock:
            self.db.execute("""CREATE TABLE IF NOT EXISTS commitments(
              commitment_id TEXT PRIMARY KEY, project TEXT NOT NULL, title TEXT NOT NULL,
              detail TEXT NOT NULL DEFAULT '{}', status TEXT NOT NULL, source TEXT NOT NULL,
              created_at REAL NOT NULL, updated_at REAL NOT NULL, completed_at REAL)""")
            self.db.execute("CREATE INDEX IF NOT EXISTS idx_commitments_project_status ON commitments(project,status,updated_at)")
            self.db.commit()
    def add(self,project,title,detail=None,source="KRISHNA",status="decided"):
        title=str(title or "").strip()
        if not title: raise ValueError("commitment title is required")
        cid=str(uuid.uuid4()); now=time.time()
        with self.lock:
            self.db.execute("INSERT INTO commitments VALUES(?,?,?,?,?,?,?,?,NULL)",
                (cid,str(project or "KRISHNA"),title,json.dumps(detail or {}),status,str(source or "KRISHNA"),now,now))
            self.db.commit()
        return self.get(cid)
    def get(self,cid):
        with self.lock:r=self.db.execute("SELECT commitment_id,project,title,detail,status,source,created_at,updated_at,completed_at FROM commitments WHERE commitment_id=?",(cid,)).fetchone()
        if not r:return None
        return {"commitment_id":r[0],"project":r[1],"title":r[2],"detail":json.loads(r[3]),"status":r[4],"source":r[5],"created_at":r[6],"updated_at":r[7],"completed_at":r[8]}
    def update(self,cid,status,detail=None):
        if status not in self.OPEN|self.DONE: raise ValueError("invalid commitment status")
        now=time.time(); completed=now if status in self.DONE else None
        with self.lock:
            if detail is None:self.db.execute("UPDATE commitments SET status=?,updated_at=?,completed_at=? WHERE commitment_id=?",(status,now,completed,cid))
            else:self.db.execute("UPDATE commitments SET status=?,detail=?,updated_at=?,completed_at=? WHERE commitment_id=?",(status,json.dumps(detail),now,completed,cid))
            self.db.commit()
        if not self.get(cid):raise KeyError(cid)
        return self.get(cid)
    def list(self,project=None,unfinished_only=False,limit=200):
        sql="SELECT commitment_id FROM commitments"; args=[]; where=[]
        if project:where.append("project=?");args.append(project)
        if unfinished_only:where.append("status NOT IN ('completed','cancelled','superseded')")
        if where:sql+=" WHERE "+" AND ".join(where)
        sql+=" ORDER BY updated_at DESC LIMIT ?";args.append(int(limit))
        with self.lock:rows=self.db.execute(sql,tuple(args)).fetchall()
        return [self.get(r[0]) for r in rows]
    def forgotten(self,project=None,older_than_seconds=86400):
        cutoff=time.time()-max(0,int(older_than_seconds))
        return [x for x in self.list(project,True,500) if x["updated_at"]<=cutoff]
    def close(self):
        with self.lock:self.db.commit();self.db.close()
