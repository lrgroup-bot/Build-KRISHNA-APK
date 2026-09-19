"""Narrow RPC surface for KRISHNA Mobile. Conversation first; no host shell passthrough."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable

_ALLOWED={"chat.send","chat.history","project.message","project.create","status.summary"}

@dataclass
class MobileRPC:
    handlers:dict[str,Callable]
    def dispatch(self,method:str,params:dict):
        if method not in _ALLOWED: raise PermissionError(f"mobile RPC denied: {method}")
        fn=self.handlers.get(method)
        if fn is None: raise KeyError(f"RPC handler unavailable: {method}")
        return fn(dict(params or {}))
