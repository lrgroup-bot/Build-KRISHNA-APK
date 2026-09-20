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

    def git_snapshot(self, root):
        rootp=Path(root).resolve()
        if not (rootp/".git").exists():return {"ok":False,"detail":"project is not a git working tree"}
        branch=self._run(["git","branch","--show-current"],rootp)
        head=self._run(["git","rev-parse","HEAD"],rootp)
        status=self._run(["git","status","--porcelain"],rootp)
        return {"ok":branch.ok and head.ok and status.ok,"branch":branch.detail.strip(),
                "head":head.detail.strip(),"clean":not bool(status.detail.strip()),"status":status.detail.strip()}

    def commit_local(self, root, message, files):
        rootp=Path(root).resolve()
        if not (rootp/".git").exists():return {"ok":False,"detail":"project is not a git working tree"}
        safe=[]
        for rel in files:
            rel=str(rel).replace("\\","/").strip("/")
            if not rel or rel.startswith("../") or "/../" in rel:raise ValueError("invalid git path")
            target=(rootp/rel).resolve()
            try:target.relative_to(rootp)
            except ValueError as exc:raise ValueError("git path escapes project") from exc
            safe.append(rel)
        if not safe:raise ValueError("explicit file list is required")
        add=self._run(["git","add","--",*safe],rootp)
        if not add.ok:return {"ok":False,"steps":[asdict(add)]}
        commit=self._run(["git","commit","-m",str(message)[:200]],rootp)
        return {"ok":commit.ok,"steps":[asdict(add),asdict(commit)],"snapshot":self.git_snapshot(root)}

    def push_current(self, root):
        rootp=Path(root).resolve(); snap=self.git_snapshot(root)
        if not snap.get("ok"):return snap
        if not snap.get("clean"):return {"ok":False,"blocked":True,"detail":"working tree must be clean before push"}
        branch=snap.get("branch")
        if not branch:return {"ok":False,"blocked":True,"detail":"detached HEAD is not pushable"}
        push=self._run(["git","push","origin",branch],rootp,300)
        return {"ok":push.ok,"steps":[asdict(push)],"branch":branch}

    @staticmethod
    def _match_api_expectations(network, expectations):
        results=[]
        for exp in expectations or []:
            needle=str(exp.get("path") or "").strip()
            method=str(exp.get("method") or "").upper()
            statuses={int(x) for x in exp.get("statuses") or [200,201,202,204]}
            matches=[x for x in network if needle and needle in str(x.get("url","")) and (not method or method==str(x.get("method","")).upper())]
            ok=any(int(x.get("status",0)) in statuses for x in matches)
            results.append({"path":needle,"method":method or None,"statuses":sorted(statuses),"ok":ok,"matches":matches[-10:]})
        return results

    def verify(self,candidate_root,checks,frontend_url=None,browser_actions=None,api_expectations=None,screenshot_path=None):
        root=Path(candidate_root).resolve();steps=[]
        allowed={"python-tests":["python","-m","unittest","discover","-s","tests"],"pytest":["python","-m","pytest","-q"],"npm-test":["npm","test","--","--runInBand"],"npm-build":["npm","run","build"],"npm-lint":["npm","run","lint"]}
        for name in checks:
            cmd=allowed.get(str(name))
            if not cmd:steps.append(DevStep(str(name),False,"verification check is not allowlisted",0));continue
            steps.append(self._run(cmd,root,300))
        browser=None
        if frontend_url:
            try:browser=self.browser.inspect(frontend_url,actions=browser_actions or [],screenshot_path=screenshot_path)
            except Exception as exc:browser={"ok":False,"findings":[{"kind":"browser_error","detail":str(exc),"severity":"error"}]}
        api_checks=self._match_api_expectations((browser or {}).get("network") or [],api_expectations)
        api_ok=all(x["ok"] for x in api_checks) if api_checks else (browser is None or bool(browser.get("network")))
        ok=bool(steps or browser) and all(x.ok for x in steps) and (browser is None or bool(browser.get("ok"))) and api_ok
        return {"verified":ok,"steps":[asdict(x) for x in steps],"browser":browser,"api_expectations":api_checks,"frontend_backend_connected":bool(browser and browser.get("ok") and api_ok)}
