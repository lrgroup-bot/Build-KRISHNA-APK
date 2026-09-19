from __future__ import annotations
import shutil,subprocess
class LocalCLIProvider:
 def __init__(self,exe,args_builder):self.exe=exe;self.args_builder=args_builder
 def available(self):return shutil.which(self.exe) is not None
 def run(self,*args):
  if not self.available():raise RuntimeError(self.exe+" unavailable")
  p=subprocess.run([self.exe,*self.args_builder(*args)],capture_output=True,text=True,shell=False)
  if p.returncode:raise RuntimeError(p.stderr[-4000:])
  return p.stdout
