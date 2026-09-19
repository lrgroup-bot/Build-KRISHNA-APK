from __future__ import annotations
import json, sqlite3, time, uuid
from threading import RLock

class TaskLedger:
    def __init__(self,path):
        self.db=sqlite3.connect(path,check_same_thread=False); self.lock=RLock()
        with self.lock:
            self.db.execute("""CREATE TABLE IF NOT EXISTS task_ledger(
              task_id TEXT PRIMARY KEY, project TEXT NOT NULL, goal TEXT NOT NULL,
              status TEXT NOT NULL, phase TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '{}',
              created_at REAL NOT NULL, updated_at REAL NOT NULL)"""); self.db.commit()
    def create(self,project,goal):
        task_id=str(uuid.uuid4()); now=time.time()
        with self.lock:self.db.execute("INSERT INTO task_ledger VALUES(?,?,?,?,?,?,?,?)",(task_id,project,goal,"queued","plan","{}",now,now));self.db.commit()
        return self.get(task_id)
    def update(self,task_id,status,phase,detail=None):
        with self.lock:self.db.execute("UPDATE task_ledger SET status=?,phase=?,detail=?,updated_at=? WHERE task_id=?",(status,phase,json.dumps(detail or {}),time.time(),task_id));self.db.commit()
        return self.get(task_id)
    def get(self,task_id):
        with self.lock:r=self.db.execute("SELECT task_id,project,goal,status,phase,detail,created_at,updated_at FROM task_ledger WHERE task_id=?",(task_id,)).fetchone()
        if not r:return None
        return {"task_id":r[0],"project":r[1],"goal":r[2],"status":r[3],"phase":r[4],"detail":json.loads(r[5]),"created_at":r[6],"updated_at":r[7]}
    def list_tasks(self, project=None, limit=100):
        with self.lock:
            if project:
                rows=self.db.execute("SELECT task_id FROM task_ledger WHERE project=? ORDER BY updated_at DESC LIMIT ?",(project,limit)).fetchall()
            else:
                rows=self.db.execute("SELECT task_id FROM task_ledger ORDER BY updated_at DESC LIMIT ?",(limit,)).fetchall()
        return [self.get(x[0]) for x in rows]

    def active(self):
        with self.lock:
            rows=self.db.execute("SELECT task_id FROM task_ledger WHERE status IN ('queued','running','verifying','waiting_approval') ORDER BY created_at").fetchall()
        return [self.get(x[0]) for x in rows]


    def close(self):
        with self.lock:
            if self.db is not None:
                self.db.commit()
                self.db.close()
                self.db = None
