import json,os,urllib.request
from .config import settings

class ModelRouter:
    """Capability-aware local/cloud model pool. Secrets are read from environment only."""
    PROVIDERS={
      "openai":{"key":"OPENAI_API_KEY","url":"https://api.openai.com/v1/chat/completions","model":"OPENAI_MODEL","default":"gpt-4o-mini"},
      "anthropic":{"key":"ANTHROPIC_API_KEY","url":"https://api.anthropic.com/v1/messages","model":"ANTHROPIC_MODEL","default":"claude-3-5-sonnet-latest"},
      "gemini":{"key":"GEMINI_API_KEY","url":"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent","model":"GEMINI_MODEL","default":"gemini-2.0-flash"},
      "xai":{"key":"XAI_API_KEY","url":"https://api.x.ai/v1/chat/completions","model":"XAI_MODEL","default":"grok-2-latest"},
      "openrouter":{"key":"OPENROUTER_API_KEY","url":"https://openrouter.ai/api/v1/chat/completions","model":"OPENROUTER_MODEL","default":"openrouter/auto"},
    }
    def local(self,prompt,model="qwen2.5:3b"):
        body=json.dumps({"model":model,"prompt":prompt,"stream":False}).encode()
        req=urllib.request.Request(settings.ollama_url.rstrip("/")+"/api/generate",data=body,headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(req,timeout=90) as r:return json.loads(r.read().decode()).get("response","")
    def available(self):
        out=[{"provider":"ollama","available":True,"local":True,"model":os.getenv("KRISHNA_LOCAL_MODEL","qwen2.5:3b")}]
        for name,p in self.PROVIDERS.items():
            out.append({"provider":name,"available":bool(os.getenv(p["key"])),"local":False,"model":os.getenv(p["model"],p["default"])})
        if settings.cloud_api_url and settings.cloud_api_key:out.append({"provider":"custom_cloud","available":True,"local":False,"model":"configured"})
        return out
    def _chat_compatible(self,name,prompt):
        p=self.PROVIDERS[name]; key=os.getenv(p["key"]); model=os.getenv(p["model"],p["default"])
        if not key:raise RuntimeError(name+" API not configured")
        if name=="gemini":
            url=p["url"].format(model=model)+"?key="+key
            body={"contents":[{"parts":[{"text":prompt}]}]};headers={"Content-Type":"application/json"}
        elif name=="anthropic":
            url=p["url"];body={"model":model,"max_tokens":4096,"messages":[{"role":"user","content":prompt}]}
            headers={"Content-Type":"application/json","x-api-key":key,"anthropic-version":"2023-06-01"}
        else:
            url=p["url"];body={"model":model,"messages":[{"role":"user","content":prompt}]}
            headers={"Content-Type":"application/json","Authorization":"Bearer "+key}
        req=urllib.request.Request(url,data=json.dumps(body).encode(),headers=headers)
        with urllib.request.urlopen(req,timeout=120) as r:data=json.loads(r.read().decode())
        if name=="gemini":return data["candidates"][0]["content"]["parts"][0]["text"]
        if name=="anthropic":return "".join(x.get("text","") for x in data.get("content",[]) if x.get("type")=="text")
        return data["choices"][0]["message"]["content"]
    def ask(self,provider,prompt):
        if provider=="ollama":return self.local(prompt,os.getenv("KRISHNA_LOCAL_MODEL","qwen2.5:3b"))
        if provider in self.PROVIDERS:return self._chat_compatible(provider,prompt)
        raise KeyError(provider)
    def coding_plan(self,privacy="approved_cloud"):
        available=[x for x in self.available() if x["available"]]
        if privacy in {"local_only","restricted"}:available=[x for x in available if x["local"]]
        preferred=["anthropic","openai","gemini","xai","openrouter","ollama"]
        available.sort(key=lambda x:preferred.index(x["provider"]) if x["provider"] in preferred else 99)
        roles=["implementation","architecture_review","bug_test_review","security_review"]
        return [{"role":role,"provider":available[i%len(available)]["provider"],"model":available[i%len(available)]["model"]} for i,role in enumerate(roles)] if available else []
    def route(self,prompt,privacy="approved_cloud"):
        try:
            out=self.local(prompt)
            if out.strip():return {"provider":"ollama","text":out}
        except Exception as exc:
            if privacy in {"local_only","restricted"}:raise RuntimeError(f"local model unavailable; cloud fallback blocked by privacy policy: {exc}")
        if privacy in {"local_only","restricted"}:raise RuntimeError("cloud fallback blocked by privacy policy")
        for row in self.available():
            if row["available"] and not row["local"] and row["provider"] in self.PROVIDERS:
                try:return {"provider":row["provider"],"text":self.ask(row["provider"],prompt)}
                except Exception:continue
        raise RuntimeError("no usable model provider")
    def auto(self,prompt):return self.route(prompt,"approved_cloud")
