from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor,as_completed
class WorkerSupervisor:
 def __init__(self,registry,max_workers=4):self.registry=registry;self.max_workers=max(1,min(int(max_workers),8))
 def run(self,jobs):
  out=[]
  with ThreadPoolExecutor(max_workers=self.max_workers,thread_name_prefix="krishna-worker") as ex:
   fs={ex.submit(self.registry.execute,j["worker"],j.get("payload") or {}):j for j in jobs}
   for f in as_completed(fs):
    j=fs[f]
    try:out.append({"worker":j["worker"],"ok":True,"result":f.result()})
    except Exception as e:out.append({"worker":j["worker"],"ok":False,"error":f"{type(e).__name__}: {e}"})
  return out
