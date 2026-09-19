from __future__ import annotations
import json
from pathlib import Path
class GraphDataset:
 """Verified-only JSONL dataset for local GNN training."""
 def __init__(self,path):self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
 def append(self,example,verified=False):
  if not verified:raise PermissionError("only verified examples may enter graph training data")
  with self.path.open("a",encoding="utf-8") as f:f.write(json.dumps(example,ensure_ascii=False)+"\n")
 def load(self):
  if not self.path.exists():return []
  return [json.loads(x) for x in self.path.read_text("utf-8").splitlines() if x.strip()]
