from __future__ import annotations
import json
from pathlib import Path
class AvatarManifest:
 def __init__(self,path):self.path=Path(path)
 def inspect(self):
  if not self.path.exists():return {"installed":False,"rigged":False,"animations":[],"morph_targets":False}
  side=self.path.with_suffix(".json")
  meta=json.loads(side.read_text("utf-8")) if side.exists() else {}
  return {"installed":True,"rigged":bool(meta.get("rigged")),"animations":meta.get("animations",[]),"morph_targets":bool(meta.get("morph_targets"))}
