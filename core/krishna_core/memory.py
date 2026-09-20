import sqlite3, time, json
from threading import RLock
from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS memory (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 project TEXT NOT NULL,
 kind TEXT NOT NULL,
 content TEXT NOT NULL,
 metadata TEXT NOT NULL DEFAULT '{}',
 created_at REAL NOT NULL,
 active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS audit (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 action TEXT NOT NULL,
 status TEXT NOT NULL,
 details TEXT NOT NULL,
 created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS incidents (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 incident_id TEXT NOT NULL UNIQUE,
 project TEXT NOT NULL,
 symptom TEXT NOT NULL,
 root_cause TEXT NOT NULL DEFAULT '',
 repair TEXT NOT NULL DEFAULT '',
 verification TEXT NOT NULL DEFAULT '{}',
 status TEXT NOT NULL,
 created_at REAL NOT NULL,
 updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS project_workspaces (
 name TEXT PRIMARY KEY,
 root TEXT NOT NULL,
 privacy TEXT NOT NULL DEFAULT 'local_only',
 allowed_actions TEXT NOT NULL DEFAULT '[]',
 verification_checks TEXT NOT NULL DEFAULT '[]',
 metadata TEXT NOT NULL DEFAULT '{}',
 created_at REAL NOT NULL,
 updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS chats (
 chat_id TEXT PRIMARY KEY,
 project TEXT NOT NULL,
 title TEXT NOT NULL,
 created_at REAL NOT NULL,
 updated_at REAL NOT NULL,
 active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS chat_messages (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 chat_id TEXT NOT NULL,
 role TEXT NOT NULL,
 content TEXT NOT NULL,
 metadata TEXT NOT NULL DEFAULT '{}',
 created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chats_project_updated ON chats(project, active, updated_at);
CREATE INDEX IF NOT EXISTS idx_chat_messages_chat ON chat_messages(chat_id, id);
CREATE INDEX IF NOT EXISTS idx_memory_project_kind ON memory(project, kind, active);\nCREATE TABLE IF NOT EXISTS learnings (\n id INTEGER PRIMARY KEY AUTOINCREMENT, project TEXT NOT NULL, topic TEXT NOT NULL, lesson TEXT NOT NULL, evidence TEXT NOT NULL DEFAULT '[]', confidence REAL NOT NULL DEFAULT 0, source TEXT NOT NULL DEFAULT 'sudarshan', status TEXT NOT NULL DEFAULT 'candidate', fingerprint TEXT NOT NULL, created_at REAL NOT NULL, updated_at REAL NOT NULL, UNIQUE(project,fingerprint));\nCREATE INDEX IF NOT EXISTS idx_learnings_project_status ON learnings(project,status,updated_at);
CREATE TABLE IF NOT EXISTS gyan_pending (
 approval_id TEXT PRIMARY KEY,
 project TEXT NOT NULL,
 topic TEXT NOT NULL,
 lesson TEXT NOT NULL,
 evidence TEXT NOT NULL DEFAULT '[]',
 confidence REAL NOT NULL DEFAULT 0,
 source TEXT NOT NULL DEFAULT 'research',
 verified INTEGER NOT NULL DEFAULT 0,
 status TEXT NOT NULL DEFAULT 'pending',
 created_at REAL NOT NULL,
 decided_at REAL
);
CREATE INDEX IF NOT EXISTS idx_gyan_pending_project_status ON gyan_pending(project,status,created_at);
CREATE INDEX IF NOT EXISTS idx_incidents_project_status ON incidents(project, status);
"""

class MemoryStore:
    def __init__(self, path=settings.db_path):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.lock = RLock()
        with self.lock:
            self.db.executescript(SCHEMA)
            self.db.commit()

    def create_gyan_pending(self, approval_id, project, topic, lesson, evidence=None, confidence=0.0, source="research", verified=False):
        now=time.time()
        with self.lock:
            self.db.execute(
                "INSERT INTO gyan_pending(approval_id,project,topic,lesson,evidence,confidence,source,verified,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (approval_id,project,topic,lesson,json.dumps(evidence or []),float(confidence or 0),source,1 if verified else 0,"pending",now),
            )
            self.db.commit()
        return self.gyan_pending(approval_id)

    def gyan_pending(self, approval_id):
        with self.lock:
            r=self.db.execute("SELECT approval_id,project,topic,lesson,evidence,confidence,source,verified,status,created_at,decided_at FROM gyan_pending WHERE approval_id=?",(approval_id,)).fetchone()
        if not r:return None
        return {"approval_id":r[0],"project":r[1],"topic":r[2],"lesson":r[3],"evidence":json.loads(r[4]),"confidence":r[5],"source":r[6],"verified":bool(r[7]),"status":r[8],"created_at":r[9],"decided_at":r[10]}

    def list_gyan_pending(self, project=None, status="pending", limit=100):
        with self.lock:
            if project:
                rows=self.db.execute("SELECT approval_id FROM gyan_pending WHERE project=? AND status=? ORDER BY created_at DESC LIMIT ?",(project,status,limit)).fetchall()
            else:
                rows=self.db.execute("SELECT approval_id FROM gyan_pending WHERE status=? ORDER BY created_at DESC LIMIT ?",(status,limit)).fetchall()
        return [self.gyan_pending(r[0]) for r in rows]

    def decide_gyan_pending(self, approval_id, status):
        if status not in {"approved","rejected"}:raise ValueError("status must be approved or rejected")
        with self.lock:
            cur=self.db.execute("UPDATE gyan_pending SET status=?,decided_at=? WHERE approval_id=? AND status='pending'",(status,time.time(),approval_id))
            self.db.commit()
        if not cur.rowcount:raise KeyError(approval_id)
        return self.gyan_pending(approval_id)

    def remember(self, project, kind, content, metadata=None):
        with self.lock:
            self.db.execute(
                "INSERT INTO memory(project,kind,content,metadata,created_at) VALUES(?,?,?,?,?)",
                (project, kind, content, json.dumps(metadata or {}), time.time())
            )
            self.db.commit()

    def recall(self, project, limit=20, kind=None):
        with self.lock:
            if kind:
                cur = self.db.execute(
                    "SELECT kind,content,metadata,created_at FROM memory "
                    "WHERE project=? AND kind=? AND active=1 ORDER BY id DESC LIMIT ?",
                    (project, kind, limit)
                )
            else:
                cur = self.db.execute(
                    "SELECT kind,content,metadata,created_at FROM memory "
                    "WHERE project=? AND active=1 ORDER BY id DESC LIMIT ?",
                    (project, limit)
                )
            return [
                {"kind": r[0], "content": r[1], "metadata": json.loads(r[2]), "created_at": r[3]}
                for r in cur.fetchall()
            ]

    def save_project(self, name, root, privacy="local_only",
                     allowed_actions=None, verification_checks=None, metadata=None):
        now = time.time()
        with self.lock:
            self.db.execute(
                """INSERT INTO project_workspaces(
                    name,root,privacy,allowed_actions,verification_checks,metadata,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?)
                ON CONFLICT(name) DO UPDATE SET
                    root=excluded.root,
                    privacy=excluded.privacy,
                    allowed_actions=excluded.allowed_actions,
                    verification_checks=excluded.verification_checks,
                    metadata=excluded.metadata,
                    updated_at=excluded.updated_at""",
                (
                    name, root, privacy, json.dumps(allowed_actions or []),
                    json.dumps(verification_checks or []), json.dumps(metadata or {}),
                    now, now,
                ),
            )
            self.db.commit()

    def delete_project(self, name):
        with self.lock:
            cur = self.db.execute("DELETE FROM project_workspaces WHERE name=?", (name,))
            self.db.commit()
            return bool(cur.rowcount)

    def projects(self):
        with self.lock:
            cur = self.db.execute(
                "SELECT name,root,privacy,allowed_actions,verification_checks,metadata,created_at,updated_at "
                "FROM project_workspaces ORDER BY name"
            )
            return [
                {
                    "name": r[0], "root": r[1], "privacy": r[2],
                    "allowed_actions": json.loads(r[3]),
                    "verification_checks": json.loads(r[4]),
                    "metadata": json.loads(r[5]),
                    "created_at": r[6], "updated_at": r[7],
                }
                for r in cur.fetchall()
            ]

    def create_chat(self, chat_id, project, title):
        now = time.time()
        with self.lock:
            self.db.execute(
                "INSERT INTO chats(chat_id,project,title,created_at,updated_at,active) VALUES(?,?,?,?,?,1)",
                (chat_id, project, title, now, now),
            )
            self.db.commit()
        return {"chat_id": chat_id, "project": project, "title": title, "created_at": now, "updated_at": now}

    def chats(self, project=None, limit=100):
        with self.lock:
            if project:
                cur = self.db.execute(
                    "SELECT chat_id,project,title,created_at,updated_at FROM chats "
                    "WHERE project=? AND active=1 ORDER BY updated_at DESC LIMIT ?",
                    (project, limit),
                )
            else:
                cur = self.db.execute(
                    "SELECT chat_id,project,title,created_at,updated_at FROM chats "
                    "WHERE active=1 ORDER BY updated_at DESC LIMIT ?",
                    (limit,),
                )
            return [
                {"chat_id": r[0], "project": r[1], "title": r[2], "created_at": r[3], "updated_at": r[4]}
                for r in cur.fetchall()
            ]

    def chat(self, chat_id):
        with self.lock:
            row = self.db.execute(
                "SELECT chat_id,project,title,created_at,updated_at FROM chats WHERE chat_id=? AND active=1",
                (chat_id,),
            ).fetchone()
            if not row:
                return None
            return {"chat_id": row[0], "project": row[1], "title": row[2], "created_at": row[3], "updated_at": row[4]}

    def move_chat(self, chat_id, project):
        project = str(project or "").strip()
        if not project:
            raise ValueError("project is required")
        with self.lock:
            row = self.db.execute("SELECT project FROM chats WHERE chat_id=? AND active=1", (chat_id,)).fetchone()
            if not row:
                raise KeyError(chat_id)
            self.db.execute("UPDATE chats SET project=?,updated_at=? WHERE chat_id=?", (project, time.time(), chat_id))
            self.db.commit()
        return self.chat(chat_id)

    def rename_chat(self, chat_id, title):
        title = str(title or "").strip()[:160]
        if not title:
            raise ValueError("title is required")
        with self.lock:
            if not self.db.execute("SELECT 1 FROM chats WHERE chat_id=? AND active=1", (chat_id,)).fetchone():
                raise KeyError(chat_id)
            self.db.execute("UPDATE chats SET title=?,updated_at=? WHERE chat_id=?", (title, time.time(), chat_id))
            self.db.commit()
        return self.chat(chat_id)

    def delete_chat(self, chat_id):
        with self.lock:
            if not self.db.execute("SELECT 1 FROM chats WHERE chat_id=? AND active=1", (chat_id,)).fetchone():
                raise KeyError(chat_id)
            now = time.time()
            self.db.execute("UPDATE chats SET active=0,updated_at=? WHERE chat_id=?", (now, chat_id))
            self.db.commit()
        return {"chat_id": chat_id, "deleted": True, "updated_at": now}

    def add_chat_message(self, chat_id, role, content, metadata=None):
        if role not in {"user", "assistant", "system", "tool"}:
            raise ValueError("invalid chat role")
        now = time.time()
        with self.lock:
            if not self.db.execute("SELECT 1 FROM chats WHERE chat_id=? AND active=1", (chat_id,)).fetchone():
                raise KeyError(chat_id)
            self.db.execute(
                "INSERT INTO chat_messages(chat_id,role,content,metadata,created_at) VALUES(?,?,?,?,?)",
                (chat_id, role, content, json.dumps(metadata or {}), now),
            )
            self.db.execute("UPDATE chats SET updated_at=? WHERE chat_id=?", (now, chat_id))
            self.db.commit()

    def chat_messages(self, chat_id, limit=40):
        with self.lock:
            rows = self.db.execute(
                "SELECT role,content,metadata,created_at FROM chat_messages "
                "WHERE chat_id=? ORDER BY id DESC LIMIT ?",
                (chat_id, limit),
            ).fetchall()
            rows.reverse()
            return [
                {"role": r[0], "content": r[1], "metadata": json.loads(r[2]), "created_at": r[3]}
                for r in rows
            ]

    def has_content_hash(self, project, digest):
        needle = f'%"sha256": "{digest}"%'
        with self.lock:
            row = self.db.execute(
                "SELECT 1 FROM memory WHERE project=? AND metadata LIKE ? AND active=1 LIMIT 1",
                (project, needle)
            ).fetchone()
            return bool(row)

    def audit(self, action, status, details):
        with self.lock:
            self.db.execute(
                "INSERT INTO audit(action,status,details,created_at) VALUES(?,?,?,?)",
                (action, status, details, time.time())
            )
            self.db.commit()

    def recent_audit(self, limit=50):
        with self.lock:
            cur = self.db.execute(
                "SELECT action,status,details,created_at FROM audit ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            return [
                {"action": r[0], "status": r[1], "details": r[2], "created_at": r[3]}
                for r in cur.fetchall()
            ]

    def save_incident(self, incident_id, project, symptom, status="investigating",
                      root_cause="", repair="", verification=None):
        now = time.time()
        with self.lock:
            self.db.execute(
                """INSERT INTO incidents(
                    incident_id,project,symptom,root_cause,repair,verification,status,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT(incident_id) DO UPDATE SET
                    root_cause=excluded.root_cause,
                    repair=excluded.repair,
                    verification=excluded.verification,
                    status=excluded.status,
                    updated_at=excluded.updated_at""",
                (
                    incident_id, project, symptom, root_cause, repair,
                    json.dumps(verification or {}), status, now, now
                )
            )
            self.db.commit()

    def incidents(self, project=None, limit=50):
        with self.lock:
            if project:
                cur = self.db.execute(
                    "SELECT incident_id,project,symptom,root_cause,repair,verification,status,created_at,updated_at "
                    "FROM incidents WHERE project=? ORDER BY id DESC LIMIT ?",
                    (project, limit)
                )
            else:
                cur = self.db.execute(
                    "SELECT incident_id,project,symptom,root_cause,repair,verification,status,created_at,updated_at "
                    "FROM incidents ORDER BY id DESC LIMIT ?",
                    (limit,)
                )
            return [
                {
                    "incident_id": r[0], "project": r[1], "symptom": r[2],
                    "root_cause": r[3], "repair": r[4],
                    "verification": json.loads(r[5]), "status": r[6],
                    "created_at": r[7], "updated_at": r[8]
                }
                for r in cur.fetchall()
            ]

    def learn(self, project, topic, lesson, evidence=None, confidence=0.0, source="sudarshan", verified=False):
        import hashlib
        project=str(project or "KRISHNA").strip(); topic=str(topic or "").strip()[:240]; lesson=str(lesson or "").strip()
        if not topic or not lesson: raise ValueError("topic and lesson are required")
        fp=hashlib.sha256((topic.lower()+"|"+lesson.lower()).encode("utf-8","ignore")).hexdigest()
        now=time.time(); status="verified" if verified else "candidate"; confidence=max(0.0,min(float(confidence),1.0))
        with self.lock:
            self.db.execute("""INSERT INTO learnings(project,topic,lesson,evidence,confidence,source,status,fingerprint,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(project,fingerprint) DO UPDATE SET evidence=excluded.evidence,confidence=MAX(learnings.confidence,excluded.confidence),source=excluded.source,status=CASE WHEN learnings.status='verified' THEN 'verified' ELSE excluded.status END,updated_at=excluded.updated_at""",
                (project,topic,lesson,json.dumps(evidence or []),confidence,str(source or "sudarshan"),status,fp,now,now))
            self.db.commit()
        return {"project":project,"topic":topic,"lesson":lesson,"confidence":confidence,"source":source,"status":status,"fingerprint":fp}

    def learnings(self, project, limit=100, verified_only=False):
        with self.lock:
            sql="SELECT topic,lesson,evidence,confidence,source,status,fingerprint,created_at,updated_at FROM learnings WHERE project=?"; args=[project]
            if verified_only: sql+=" AND status='verified'"
            sql+=" ORDER BY updated_at DESC LIMIT ?"; args.append(int(limit))
            rows=self.db.execute(sql,tuple(args)).fetchall()
        return [{"topic":r[0],"lesson":r[1],"evidence":json.loads(r[2]),"confidence":r[3],"source":r[4],"status":r[5],"fingerprint":r[6],"created_at":r[7],"updated_at":r[8]} for r in rows]

    def verify_learning(self, project, fingerprint):
        with self.lock:
            cur=self.db.execute("UPDATE learnings SET status='verified',updated_at=? WHERE project=? AND fingerprint=?",(time.time(),project,fingerprint)); self.db.commit()
        if not cur.rowcount: raise KeyError(fingerprint)
        return True

    def close(self):
        with self.lock:
            if self.db is not None:
                self.db.commit()
                self.db.close()
                self.db = None
