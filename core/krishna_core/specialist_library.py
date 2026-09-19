from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import json, re, time

DIVISIONS = ("academic","design","engineering","finance","game-development","gis","healthcare","marketing","paid-media","product","project-management","research","sales","security","spatial-computing","specialized","support","testing")
FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)

@dataclass(slots=True)
class Specialist:
    id: str
    name: str
    division: str
    description: str
    source_path: str
    source: str = "agency-agents"
    enabled: bool = True
    risk: str = "advisory"
    loaded_at: float = 0.0

class SpecialistLibrary:
    """Indexes prompt-only specialists as on-demand contexts; never executes repo scripts."""
    def __init__(self, state_dir: str|Path, source_root: str|Path|None=None):
        self.state=Path(state_dir); self.state.mkdir(parents=True,exist_ok=True)
        self.config=self.state/"specialists.json"
        self.source_root=Path(source_root).resolve() if source_root else None
        self.items={}
        self._load()

    def _load(self):
        if not self.config.exists(): return
        try:
            raw=json.loads(self.config.read_text(encoding="utf-8"))
            for row in raw.get("specialists",[]):
                s=Specialist(**row); self.items[s.id]=s
        except Exception: self.items={}

    def _save(self):
        self.config.write_text(json.dumps({"source_root":str(self.source_root) if self.source_root else None,"specialists":[asdict(x) for x in self.items.values()]},indent=2),encoding="utf-8")

    @staticmethod
    def _field(block,key):
        m=re.search(rf"(?mi)^\s*{re.escape(key)}\s*:\s*[\"']?(.*?)[\"']?\s*$",block)
        return (m.group(1).strip() if m else "")

    def index(self, source_root: str|Path|None=None):
        if source_root: self.source_root=Path(source_root).resolve()
        if not self.source_root or not self.source_root.exists(): raise ValueError("specialist source directory not found")
        found={}
        for division in DIVISIONS:
            d=self.source_root/division
            if not d.is_dir(): continue
            for p in sorted(d.glob("*.md")):
                text=p.read_text(encoding="utf-8",errors="replace")
                m=FRONTMATTER.match(text)
                if not m: continue
                name=self._field(m.group(1),"name") or p.stem.replace("-"," ").title()
                desc=self._field(m.group(1),"description")
                sid=f"{division}/{p.stem}"
                found[sid]=Specialist(sid,name,division,desc,str(p),loaded_at=time.time())
        self.items=found; self._save()
        return self.status()

    def status(self):
        counts={}
        for x in self.items.values(): counts[x.division]=counts.get(x.division,0)+1
        return {"source_root":str(self.source_root) if self.source_root else None,"total":len(self.items),"divisions":counts,"specialists":[asdict(x) for x in sorted(self.items.values(),key=lambda z:(z.division,z.name.lower()))]}

    def select(self, task:str, limit:int=5):
        words={w for w in re.findall(r"[a-z0-9+#.-]{3,}",task.lower())}
        scored=[]
        for x in self.items.values():
            hay=(x.name+" "+x.description+" "+x.division).lower()
            score=sum(1 for w in words if w in hay)
            if x.division=="testing": score+=1
            if "code" in words and x.division=="engineering": score+=2
            if score: scored.append((score,x))
        scored.sort(key=lambda q:(-q[0],q[1].name))
        return [asdict(x) for _,x in scored[:max(1,min(limit,8))]]

    def context(self, specialist_id:str, max_chars:int=14000):
        x=self.items.get(specialist_id)
        if not x: raise KeyError(specialist_id)
        p=Path(x.source_path).resolve()
        if self.source_root not in p.parents: raise PermissionError("specialist path escaped source root")
        return {"specialist":asdict(x),"instructions":p.read_text(encoding="utf-8",errors="replace")[:max_chars]}
