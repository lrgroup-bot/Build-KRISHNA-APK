from __future__ import annotations
from pathlib import Path
import shutil,tempfile
class PromotionRuntime:
 """Promote verified shadow files with backup + rollback."""
 def promote(self,shadow,working,relative_files,verified):
  if not verified:raise PermissionError("verification required before promotion")
  shadow,working=Path(shadow),Path(working)
  backup=Path(tempfile.mkdtemp(prefix="krishna-backup-"))
  changed=[]
  try:
   for rel in relative_files:
    src=shadow/rel;dst=working/rel
    if not src.exists():raise FileNotFoundError(str(src))
    if dst.exists():
     b=backup/rel;b.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dst,b)
    dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);changed.append(rel)
   return {"promoted":True,"files":changed,"backup":str(backup)}
  except Exception:
   for rel in changed:
    b=backup/rel;dst=working/rel
    if b.exists():shutil.copy2(b,dst)
    elif dst.exists():dst.unlink()
   raise
 def rollback(self,working,backup,relative_files):
  working,backup=Path(working),Path(backup)
  for rel in relative_files:
   b=backup/rel;dst=working/rel
   if b.exists():dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(b,dst)
   elif dst.exists():dst.unlink()
  return {"rolled_back":True,"files":list(relative_files)}
