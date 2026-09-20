from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
import os, shutil, subprocess, tempfile, time

@dataclass
class DevStep:
    name: str
    ok: bool
    detail: str
    elapsed_ms: int

class DevelopmentOperator:
    """Bounded local coding loop. Natural language is never executed as shell."""
    def __init__(self,browser): self.browser=browser

    @staticmethod
    def _run(args,cwd,timeout=180):
        started=time.perf_counter()
        try:
            p=subprocess.run(args,cwd=str(cwd),capture_output=True,text=True,timeout=timeout,shell=False,env=os.environ.copy())
            out=((p.stdout or "")+"\n"+(p.stderr or "")).strip()[-12000:]
            return DevStep(" ".join(args[:2]),p.returncode==0,out or f"exit={p.returncode}",int((time.perf_counter()-started)*1000))
        except Exception as exc:
            return DevStep(" ".join(args[:2]),False,f"{type(exc).__name__}: {exc}",int((time.perf_counter()-started)*1000))

    def sync(self,root):
        rootp=Path(root).resolve()
        if not (rootp/".git").exists(): return {"ok":False,"changed":False,"detail":"project is not a git working tree"}
        fetch=self._run(["git","fetch","--prune","origin"],rootp)
        if not fetch.ok:return {"ok":False,"changed":False,"steps":[asdict(fetch)]}
        status=self._run(["git","status","--porcelain"],rootp)
        if not status.ok or status.detail.strip():
            return {"ok":False,"changed":False,"blocked":True,"detail":"local working tree is not clean; refusing automatic pull","steps":[asdict(fetch),asdict(status)]}
        pull=self._run(["git","pull","--ff-only","origin"],rootp)
        return {"ok":pull.ok,"changed":pull.ok,"steps":[asdict(fetch),asdict(status),asdict(pull)]}

    def stage(self,root,files):
        source=Path(root).resolve()
        if not source.is_dir():raise ValueError("project root does not exist")
        parent=source.parent/".krishna_state"/"dev-candidates";parent.mkdir(parents=True,exist_ok=True)
        candidate=Path(tempfile.mkdtemp(prefix="candidate-",dir=str(parent)))
        shutil.copytree(source,candidate,dirs_exist_ok=True,ignore=shutil.ignore_patterns(".git","node_modules",".venv","__pycache__","dist","build"))
        changed=[]
        for item in files:
            rel=str(item.get("path","")).replace("\\","/").strip("/")
            if not rel or rel.startswith("../") or "/../" in rel:raise ValueError("invalid relative file path")
            target=(candidate/rel).resolve()
            try:target.relative_to(candidate)
            except ValueError as exc:raise ValueError("file escapes candidate root") from exc
            target.parent.mkdir(parents=True,exist_ok=True);target.write_text(str(item.get("content","")),encoding="utf-8");changed.append(rel)
        return {"candidate_root":str(candidate),"files":changed,"file_count":len(changed)}

    def verify(self,candidate_root,checks,frontend_url=None):
        root=Path(candidate_root).resolve();steps=[]
        allowed={"python-tests":["python","-m","unittest","discover","-s","tests"],"pytest":["python","-m","pytest","-q"],"npm-test":["npm","test","--","--runInBand"],"npm-build":["npm","run","build"],"npm-lint":["npm","run","lint"]}
        for name in checks:
            cmd=allowed.get(str(name))
            if not cmd:steps.append(DevStep(str(name),False,"verification check is not allowlisted",0));continue
            steps.append(self._run(cmd,root,300))
        browser=None
        if frontend_url:
            try:browser=self.browser.inspect(frontend_url)
            except Exception as exc:browser={"ok":False,"findings":[{"kind":"browser_error","detail":str(exc),"severity":"error"}]}
        ok=bool(steps or browser) and all(x.ok for x in steps) and (browser is None or bool(browser.get("ok")))
        return {"verified":ok,"steps":[asdict(x) for x in steps],"browser":browser,"frontend_backend_connected":bool(browser and browser.get("ok") and browser.get("network"))}
