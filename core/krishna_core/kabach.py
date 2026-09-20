from __future__ import annotations
from dataclasses import dataclass,asdict
from pathlib import Path
from urllib.parse import urlparse
import hashlib,ipaddress,json,re,time

_SECRET_PATTERNS=(
 r"(?i)(api[_-]?key|secret|token|password|passwd|private[_-]?key)\s*[:=]\s*[^\s,;]{6,}",
 r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
 r"(?i)authorization:\s*(?:bearer|basic)\s+\S+",
)
_SENSITIVE_NAMES={".env",".git-credentials","id_rsa","id_ed25519","credentials","credentials.json"}

@dataclass(frozen=True,slots=True)
class KabachVerdict:
    allowed:bool; action:str; reason:str; risk:str; evidence:tuple[str,...]; receipt:str
    def as_dict(self): return asdict(self)

class KabachAgent:
    """Deterministic fail-closed security boundary for KRISHNA. It advises/enforces policy; KRISHNA remains authority."""
    def __init__(self,memory):
        self.memory=memory

    def _receipt(self,payload):
        return hashlib.sha256(json.dumps(payload,sort_keys=True,default=str).encode()).hexdigest()

    def inspect_text(self,text,source="unknown"):
        raw=str(text or ""); hits=[]
        for p in _SECRET_PATTERNS:
            if re.search(p,raw): hits.append(p)
        payload={"kind":"text","source":source,"secret_indicators":len(hits),"ts":int(time.time())}
        return KabachVerdict(not hits,"allow" if not hits else "block","clean" if not hits else "possible secret/credential exposure","low" if not hits else "critical",tuple(hits),self._receipt(payload)).as_dict()

    def inspect_path(self,path,project_root=None,write=False):
        p=Path(path).expanduser().resolve(); evidence=[]
        if p.name.lower() in _SENSITIVE_NAMES or any(x.lower() in {"secrets",".ssh",".gnupg"} for x in p.parts): evidence.append("sensitive_path")
        if project_root:
            root=Path(project_root).expanduser().resolve()
            try:p.relative_to(root)
            except ValueError:evidence.append("outside_project_scope")
        blocked=bool(evidence)
        payload={"kind":"path","path":str(p),"write":write,"evidence":evidence}
        return KabachVerdict(not blocked,"allow" if not blocked else "block","scoped path" if not blocked else "path policy violation","low" if not blocked else "high",tuple(evidence),self._receipt(payload)).as_dict()

    def inspect_egress(self,url,method="GET",allowed_domains=None,payload=None):
        parsed=urlparse(str(url or "")); host=(parsed.hostname or "").lower(); evidence=[]
        if parsed.scheme not in {"https"}: evidence.append("non_https_or_invalid")
        try:
            ip=ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved: evidence.append("private_or_reserved_ip")
        except ValueError: pass
        allowed={x.lower().strip() for x in (allowed_domains or []) if str(x).strip()}
        if not allowed: evidence.append("egress_default_deny")
        elif host not in allowed and not any(host.endswith("."+x) for x in allowed): evidence.append("domain_not_allowlisted")
        text=self.inspect_text(json.dumps(payload or {},default=str),"egress_payload")
        if not text["allowed"]: evidence.append("secret_in_payload")
        blocked=bool(evidence)
        data={"kind":"egress","host":host,"method":method.upper(),"evidence":evidence}
        return KabachVerdict(not blocked,"allow" if not blocked else "block","allowlisted secure egress" if not blocked else "egress policy violation","low" if not blocked else "critical",tuple(evidence),self._receipt(data)).as_dict()

    def inspect_tool(self,tool,operation,permissions=None,approved=False):
        perms=set(permissions or []); evidence=[]; op=str(operation or "").lower()
        dangerous=any(x in op for x in ("delete","format","credential","secret","disable_security","privilege","shell"))
        if dangerous:evidence.append("high_risk_operation")
        if tool not in perms and "*" not in perms:evidence.append("tool_not_permitted")
        if dangerous and not approved:evidence.append("explicit_approval_required")
        blocked=bool(evidence)
        data={"kind":"tool","tool":tool,"operation":operation,"evidence":evidence}
        return KabachVerdict(not blocked,"allow" if not blocked else "block","policy satisfied" if not blocked else "tool policy violation","low" if not blocked else "high",tuple(evidence),self._receipt(data)).as_dict()

    def research_security(self, project, question, garuda, limit=10):
        question=str(question or "").strip()
        if not question: raise ValueError("security research question is required")
        report=garuda.scout(project,"cybersecurity defensive research "+question,limit)
        safe=[]
        for row in (report.get("web") or []):
            if not row.get("suspicious"): safe.append(row)
        repos=[]
        for row in (report.get("github") or []):
            repos.append(row)
        result={"agent":"KABACH","project":project,"question":question,"garuda_report":report,
            "defensive_evidence":safe,"repository_candidates":repos,
            "policy":{"purpose":"defensive_security_only","auto_execute_external_code":False,"auto_install":False,"decision_authority":"KRISHNA","implementation_executor":"Sudarshan"}}
        self.memory.remember(project,"kabach_security_research",question,{"result":result})
        self.memory.audit("kabach_security_research","completed",f"{project}:{len(safe)} web:{len(repos)} repos")
        return result

    def protect_project(self,project,root,privacy="local_only"):
        checks=[]
        for name in (".env",".git/config","requirements.txt","pyproject.toml","package.json","package-lock.json"):
            p=Path(root)/name
            if p.exists(): checks.append({"path":str(p),"verdict":self.inspect_path(p,root,False)})
        return {"agent":"KABACH","project":project,"root":str(Path(root).resolve()),"checks":checks,"privacy":privacy,"protected":True,"controls":["secret_scan","path_scope","egress_default_deny","tool_permission_gate","audit_receipts","untrusted_content_boundary"],"policy":{"egress":"default_deny","secrets":"never_transmit","project_scope":"enforced","external_content":"untrusted","security_research":"delegate_to_garuda","decision_authority":"KRISHNA"}}

    def gate_external_evidence(self,text,source="external"):
        verdict=self.inspect_text(text,source)
        return {"allowed_as_data":True,"allowed_as_instruction":False,"secret_safe":verdict["allowed"],"verdict":verdict}

    def record(self,project,verdict,context=""):
        status="allowed" if verdict.get("allowed") else "blocked"
        self.memory.audit("kabach_"+context,status,json.dumps({"project":project,"verdict":verdict},default=str)[:12000])
        return verdict
