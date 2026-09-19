"""Single guarded entry point for model and swarm intelligence."""
from __future__ import annotations
from dataclasses import dataclass
from .content_guard import ContentGuard
from .model_router import ModelRequest, ModelRouter
from .ruflo_adapter import RufloAdapter

@dataclass
class IntelligenceGateway:
    router: ModelRouter
    ruflo: RufloAdapter

    @classmethod
    def create(cls): return cls(ModelRouter(),RufloAdapter())

    def reason(self, text:str, task:str="general")->dict:
        # External material remains untrusted data. Existing KRISHNA ContentGuard
        # is the policy boundary; models cannot convert retrieved text into host commands.
        guard=ContentGuard()
        inspected=guard.inspect(text) if hasattr(guard,"inspect") else None
        if inspected is not None and getattr(inspected,"blocked",False):
            return {"ok":False,"blocked":True,"reason":getattr(inspected,"reason","content guard")}
        result=self.router.complete(ModelRequest(prompt=text,task=task))
        return {"ok":True,"blocked":False,**result}

    def swarm_health(self)->dict: return self.ruflo.health()
