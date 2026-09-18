import sqlite3, time, json
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
"""

class MemoryStore:
    def __init__(self, path=settings.db_path):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.executescript(SCHEMA)
        self.db.commit()
    def remember(self, project, kind, content, metadata=None):
        self.db.execute("INSERT INTO memory(project,kind,content,metadata,created_at) VALUES(?,?,?,?,?)",(project,kind,content,json.dumps(metadata or {}),time.time()))
        self.db.commit()
    def recall(self, project, limit=20):
        cur=self.db.execute("SELECT kind,content,metadata,created_at FROM memory WHERE project=? AND active=1 ORDER BY id DESC LIMIT ?",(project,limit))
        return [{"kind":r[0],"content":r[1],"metadata":json.loads(r[2]),"created_at":r[3]} for r in cur.fetchall()]
    def audit(self, action, status, details):
        self.db.execute("INSERT INTO audit(action,status,details,created_at) VALUES(?,?,?,?)",(action,status,details,time.time()))
        self.db.commit()
