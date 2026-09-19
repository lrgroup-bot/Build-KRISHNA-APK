"""Bounded Ruflo adapter for KRISHNA.

Ruflo is an optional worker/orchestrator. It never becomes KRISHNA's authority.
Commands are allowlisted and executed without a shell.
"""
from __future__ import annotations
import json, shutil, subprocess
from dataclasses import dataclass

_ALLOWED={"status","agent","swarm","memory","hooks","health"}

@dataclass(frozen=True)
class RufloResult:
    ok: bool; command: tuple[str,...]; stdout: str; stderr: str; returncode: int

class RufloAdapter:
    def __init__(self, executable:str="npx", package:str="ruflo@latest", timeout:int=120):
        self.executable=executable; self.package=package; self.timeout=timeout
    def available(self)->bool: return shutil.which(self.executable) is not None
    def run(self, command:str, *args:str)->RufloResult:
        if command not in _ALLOWED: raise PermissionError(f"Ruflo command not allowed: {command}")
        if not self.available(): return RufloResult(False,(self.executable,),"", "npx unavailable",127)
        argv=[self.executable,"--yes",self.package,command,*map(str,args)]
        p=subprocess.run(argv,capture_output=True,text=True,timeout=self.timeout,shell=False)
        return RufloResult(p.returncode==0,tuple(argv),p.stdout[-20000:],p.stderr[-20000:],p.returncode)
    def health(self)->dict:
        r=self.run("health")
        return {"available":self.available(),"ok":r.ok,"returncode":r.returncode,"stdout":r.stdout,"stderr":r.stderr}
