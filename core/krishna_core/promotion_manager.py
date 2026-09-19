from __future__ import annotations
from pathlib import Path
import hashlib, json, shutil, time, uuid

IGNORED={".git",".venv","venv","node_modules","__pycache__","dist","build"}

class PromotionManager:
    """Transactional promotion with backup, post-checks and automatic rollback."""
    def __init__(self,backup_root):
        self.backup_root=Path(backup_root).resolve(); self.backup_root.mkdir(parents=True,exist_ok=True)

    @staticmethod
    def _files(root):
        root=Path(root)
        return sorted(p for p in root.rglob("*") if p.is_file() and not any(x in IGNORED for x in p.relative_to(root).parts))

    @staticmethod
    def _digest(path):
        h=hashlib.sha256()
        with Path(path).open("rb") as f:
            for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
        return h.hexdigest()

    def diff(self,live_root,candidate_root):
        live=Path(live_root).resolve(); candidate=Path(candidate_root).resolve()
        if not live.is_dir() or not candidate.is_dir(): raise ValueError("live and candidate roots must be directories")
        a={str(p.relative_to(live)):self._digest(p) for p in self._files(live)}
        b={str(p.relative_to(candidate)):self._digest(p) for p in self._files(candidate)}
        added=sorted(set(b)-set(a)); removed=sorted(set(a)-set(b))
        changed=sorted(k for k in set(a)&set(b) if a[k]!=b[k])
        return {"added":added,"changed":changed,"removed":removed,"file_count":len(added)+len(changed)+len(removed)}

    def promote(self,project,live_root,candidate_root,verify):
        live=Path(live_root).resolve(); candidate=Path(candidate_root).resolve(); delta=self.diff(live,candidate)
        if not delta["file_count"]: return {"status":"no_changes","promoted":False,"rolled_back":False,"diff":delta}
        txid=str(uuid.uuid4()); backup=self.backup_root/project/txid; backup.mkdir(parents=True,exist_ok=False)
        (backup/"manifest.json").write_text(json.dumps({"transaction_id":txid,"project":project,"live_root":str(live),"created_at":time.time(),"diff":delta},indent=2),encoding="utf-8")
        for rel in delta["changed"]+delta["removed"]:
            src=live/rel; dst=backup/"files"/rel; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
        try:
            for rel in delta["added"]+delta["changed"]:
                src=candidate/rel; dst=live/rel; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
            for rel in delta["removed"]:
                p=live/rel
                if p.exists(): p.unlink()
            verification=verify(live)
            if not verification.get("verified"):
                self.rollback(live,backup,delta)
                return {"status":"rolled_back","promoted":False,"rolled_back":True,"transaction_id":txid,"backup":str(backup),"diff":delta,"verification":verification}
            return {"status":"promoted","promoted":True,"rolled_back":False,"transaction_id":txid,"backup":str(backup),"diff":delta,"verification":verification}
        except Exception:
            self.rollback(live,backup,delta); raise

    @staticmethod
    def rollback(live,backup,delta):
        live=Path(live); backup=Path(backup)
        for rel in delta["added"]:
            p=live/rel
            if p.exists(): p.unlink()
        for rel in delta["changed"]+delta["removed"]:
            src=backup/"files"/rel; dst=live/rel; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
        return True
