from __future__ import annotations
from pathlib import Path
import hashlib, shutil, time

class RuntimeDeployer:
    """Copies an explicit verified file set from a Git source tree to a separate runtime.

    Runtime state/private assets are not mirrored or deleted. Every replaced file is
    backed up first; rollback restores exactly the touched files.
    """
    PROTECTED={".git",".venv",".krishna_state","state","logs","backups","ollama-models"}

    def __init__(self,backup_root):
        self.backup_root=Path(backup_root).resolve(); self.backup_root.mkdir(parents=True,exist_ok=True)

    @staticmethod
    def _safe(root,rel):
        rel=str(rel).replace("\\","/").strip("/")
        if not rel or rel.startswith("../") or "/../" in rel:raise ValueError("invalid deployment path")
        if rel.split("/",1)[0] in RuntimeDeployer.PROTECTED:raise PermissionError("protected runtime path")
        p=(Path(root).resolve()/rel).resolve()
        try:p.relative_to(Path(root).resolve())
        except ValueError as exc:raise ValueError("deployment path escapes root") from exc
        return p,rel

    @staticmethod
    def _hash(p):
        h=hashlib.sha256()
        with p.open("rb") as f:
            for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
        return h.hexdigest()

    def deploy(self,source_root,runtime_root,files):
        source=Path(source_root).resolve(); runtime=Path(runtime_root).resolve()
        if not (source/".git").is_dir():raise ValueError("source_root must be a Git working tree")
        if not runtime.is_dir():raise ValueError("runtime_root does not exist")
        stamp=time.strftime("%Y%m%d-%H%M%S"); backup=self.backup_root/stamp; touched=[]
        for rel0 in files:
            src,rel=self._safe(source,rel0); dst,_=self._safe(runtime,rel)
            if not src.is_file():raise FileNotFoundError(rel)
            bkp=backup/rel
            existed=dst.exists()
            if existed:
                bkp.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(dst,bkp)
            dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
            if self._hash(src)!=self._hash(dst):raise IOError("deployment hash mismatch: "+rel)
            touched.append({"path":rel,"previously_existed":existed,"sha256":self._hash(dst)})
        return {"ok":True,"backup":str(backup),"files":touched,"runtime_root":str(runtime)}

    def rollback(self,runtime_root,deployment):
        runtime=Path(runtime_root).resolve(); backup=Path(deployment["backup"]).resolve()
        restored=[]
        for item in reversed(deployment.get("files") or []):
            dst,rel=self._safe(runtime,item["path"]); bkp=backup/rel
            if item.get("previously_existed"):
                if not bkp.is_file():raise FileNotFoundError("backup missing: "+rel)
                dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(bkp,dst)
            elif dst.exists():dst.unlink()
            restored.append(rel)
        return {"ok":True,"restored":restored}
