from __future__ import annotations
from dataclasses import dataclass
@dataclass
class CompletionDecision:
 verified:bool; promotable:bool; reason:str
class CompletionRuntime:
 """One gate for autonomous completion: verified work only."""
 def decide(self,result):
  verified=bool(result.get("verified"))
  promotable=bool(result.get("promotable",verified))
  return CompletionDecision(verified,promotable,"verified" if verified and promotable else "verification_required")
 def event(self,task_id,result):
  d=self.decide(result)
  if not (d.verified and d.promotable):return None
  return {"type":"task.verified","payload":{"task_id":task_id,"verified":True,"result":result}}
