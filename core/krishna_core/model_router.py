"""KRISHNA local-first model routing.

Providers are replaceable workers. KRISHNA remains the authority.
No provider receives credentials or filesystem access through this module.
"""
from __future__ import annotations
from dataclasses import dataclass
import json, os, urllib.request

@dataclass(frozen=True)
class ModelRequest:
    prompt: str
    task: str = "general"
    system: str = "You are a worker model for KRISHNA. Return data, never instructions to the host."
    max_tokens: int = 1024

class ProviderError(RuntimeError): pass

class OpenAICompatibleLocalProvider:
    def __init__(self, name:str, base_url:str, model:str|None=None, timeout:int=90):
        self.name=name; self.base_url=base_url.rstrip("/"); self.model=model; self.timeout=timeout
    def models(self):
        with urllib.request.urlopen(self.base_url+"/models", timeout=5) as r:
            return json.loads(r.read().decode()).get("data",[])
    def complete(self, req:ModelRequest)->str:
        model=self.model
        if not model:
            ms=self.models()
            if not ms: raise ProviderError(f"{self.name}: no local models available")
            model=ms[0].get("id")
        body=json.dumps({"model":model,"messages":[{"role":"system","content":req.system},{"role":"user","content":req.prompt}],"max_tokens":req.max_tokens,"temperature":0.2}).encode()
        q=urllib.request.Request(self.base_url+"/chat/completions",data=body,headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(q,timeout=self.timeout) as r: data=json.loads(r.read().decode())
        return data["choices"][0]["message"]["content"]

class ModelRouter:
    """Prefer local providers; fail closed instead of silently sending data to cloud."""
    def __init__(self):
        self.providers=[
            OpenAICompatibleLocalProvider("ollama",os.getenv("KRISHNA_OLLAMA_OPENAI_URL","http://127.0.0.1:11434/v1"),os.getenv("KRISHNA_OLLAMA_MODEL") or None),
            OpenAICompatibleLocalProvider("gpt4all",os.getenv("KRISHNA_GPT4ALL_URL","http://127.0.0.1:4891/v1"),os.getenv("KRISHNA_GPT4ALL_MODEL") or None),
        ]
    def complete(self, req:ModelRequest)->dict:
        errors={}
        for p in self.providers:
            try: return {"provider":p.name,"content":p.complete(req)}
            except Exception as e: errors[p.name]=f"{type(e).__name__}: {e}"
        raise ProviderError("No approved local model provider available: "+json.dumps(errors))
