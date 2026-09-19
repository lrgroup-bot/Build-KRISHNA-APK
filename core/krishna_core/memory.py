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
CREATE INDEX IF NOT EXISTS idx_memory_project_kind ON memory(project, kind, active);
CREATE INDEX IF NOT EXISTS idx_incidents_project_status ON incidents(project, status);
"""

class MemoryStore:
    def __init__(self, path=settings.db_path):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.lock = RLock()
        with self.lock:
            self.db.executescript(SCHEMA)
            self.db.commit()

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
