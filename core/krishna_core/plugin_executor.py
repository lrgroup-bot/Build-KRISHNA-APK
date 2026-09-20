from __future__ import annotations
import json, os, urllib.request, urllib.parse
from dataclasses import dataclass
from pathlib import Path

@dataclass
class PluginCall:
    plugin_id:str
    project:str
    operation:str
    payload:dict

class PluginExecutor:
    """Execution boundary for enabled HTTP plugins.

    Secrets are never stored in plugin manifests. auth_env names an environment
    variable supplied by the owner/runtime. Local/connector/MCP execution stays
    adapter-specific instead of becoming arbitrary shell execution.
    """
    def __init__(self, registry):
        self.registry=registry

    def _manifest(self, plugin_id):
        item=next((x for x in self.registry.list() if x["id"]==plugin_id),None)
        if not item: raise KeyError(plugin_id)
        if not item.get("enabled"): raise PermissionError("plugin is disabled")
        return item

    def execute(self, plugin_id, project, operation="get", payload=None, auth_env=None):
        item=self._manifest(plugin_id)
        scope=item.get("project_scope") or ["*"]
        if "*" not in scope and project not in scope: raise PermissionError("plugin is outside project scope")
        if item.get("kind")!="http":
            raise ValueError("this runtime executes HTTP plugins only; connector/MCP/local plugins require their registered adapter")
        endpoint=str(item.get("endpoint") or "").strip()
        parsed=urllib.parse.urlparse(endpoint)
        if parsed.scheme not in {"http","https"} or not parsed.hostname: raise ValueError("invalid HTTP plugin endpoint")
        op=str(operation or "get").lower()
        if op not in {"get","post"}: raise ValueError("HTTP plugin operation must be get or post")
        headers={"Accept":"application/json","User-Agent":"KRISHNA-PluginRuntime/1.0"}
        if auth_env:
            name=str(auth_env)
            if not name.replace("_","").isalnum(): raise ValueError("invalid auth environment variable")
            secret=os.getenv(name)
            if not secret: raise PermissionError("plugin credential environment variable is unavailable")
            auth=item.get("auth_type")
            if auth=="token": headers["Authorization"]="Bearer "+secret
            elif auth=="api_key": headers["X-API-Key"]=secret
            elif auth not in {"none","local"}: raise ValueError("auth type requires a dedicated adapter")
        data=None
        if op=="post":
            data=json.dumps(payload or {}).encode("utf-8"); headers["Content-Type"]="application/json"
        req=urllib.request.Request(endpoint,data=data,headers=headers,method=op.upper())
        with urllib.request.urlopen(req,timeout=30) as response:
            raw=response.read(2_000_001)
            if len(raw)>2_000_000: raise ValueError("plugin response exceeds 2 MB")
            ctype=response.headers.get("Content-Type","")
            text=raw.decode("utf-8",errors="replace")
            body=json.loads(text) if "json" in ctype else text
            return {"plugin_id":plugin_id,"project":project,"status":response.status,"content_type":ctype,"body":body}
