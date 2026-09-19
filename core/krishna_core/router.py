import json, urllib.request
from .config import settings


class ModelRouter:
    def local(self, prompt, model="qwen2.5:3b"):
        body=json.dumps({"model":model,"prompt":prompt,"stream":False}).encode()
        req=urllib.request.Request(
            settings.ollama_url.rstrip("/")+"/api/generate",
            data=body,
            headers={"Content-Type":"application/json"},
        )
        with urllib.request.urlopen(req,timeout=90) as r:
            return json.loads(r.read().decode()).get("response","")

    def cloud(self, prompt):
        if not settings.cloud_api_url or not settings.cloud_api_key:
            raise RuntimeError("Cloud API not configured")
        body=json.dumps({"message":prompt}).encode()
        req=urllib.request.Request(
            settings.cloud_api_url,
            data=body,
            headers={"Content-Type":"application/json","Authorization":"Bearer "+settings.cloud_api_key},
        )
        with urllib.request.urlopen(req,timeout=90) as r:
            data=json.loads(r.read().decode())
            return data.get("reply") or data.get("response") or json.dumps(data)

    def route(self, prompt, privacy="approved_cloud"):
        try:
            out=self.local(prompt)
            if out.strip():
                return {"provider":"local","text":out}
        except Exception as local_exc:
            if privacy in {"local_only", "restricted"}:
                raise RuntimeError(f"local model unavailable; cloud fallback blocked by privacy policy: {local_exc}")
        if privacy in {"local_only", "restricted"}:
            raise RuntimeError("cloud fallback blocked by privacy policy")
        return {"provider":"cloud","text":self.cloud(prompt)}

    def auto(self, prompt):
        return self.route(prompt, privacy="approved_cloud")
