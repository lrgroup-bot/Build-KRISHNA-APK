"""Single guarded entry point for model and swarm intelligence."""
from __future__ import annotations
from dataclasses import dataclass
from .content_guard import guarded_excerpt
from .model_router import ModelRequest, ModelRouter
from .ruflo_adapter import RufloAdapter

@dataclass
class IntelligenceGateway:
    router: ModelRouter
    ruflo: RufloAdapter

    @classmethod
    def create(cls): return cls(ModelRouter(),RufloAdapter())

    def reason(self, text:str, task:str="general", source:str="external")->dict:
        assessment, wrapped = guarded_excerpt(text, source=source)
        # Suspicious content is still analyzable as evidence, but is explicitly wrapped
        # and cannot grant itself tool/host authority.
        result=self.router.complete(ModelRequest(prompt=wrapped,task=task))
        return {"ok":True,"trust":assessment,"provider":result["provider"],"content":result["content"]}

    def swarm_health(self)->dict: return self.ruflo.health()
