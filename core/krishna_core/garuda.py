from __future__ import annotations
import re, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from .content_guard import assess_untrusted_content

@dataclass
class WebCandidate:
    title:str
    url:str
    summary:str
    source:str
    relevance:int
    suspicious:bool=False

class GarudaAgent:
    """Read-only discovery scout. Garuda researches; KRISHNA decides and implements."""
    def __init__(self, github, memory):
        self.github=github; self.memory=memory

    @staticmethod
    def _terms(text):
        return {x for x in re.findall(r"[a-z0-9][a-z0-9_+.-]{2,}",str(text).lower()) if len(x)>2}

    def _web(self, query, limit=10):
        url="https://www.bing.com/search?format=rss&q="+urllib.parse.quote(query)
        req=urllib.request.Request(url,headers={"User-Agent":"KRISHNA-Garuda/1.0"})
        with urllib.request.urlopen(req,timeout=20) as r:
            root=ET.fromstring(r.read())
        wanted=self._terms(query); out=[]
        for item in root.findall(".//item")[:max(1,min(int(limit),20))]:
            title=item.findtext("title") or ""; link=item.findtext("link") or ""
            summary=item.findtext("description") or ""
            guard=assess_untrusted_content(title+"\n"+summary,link).as_dict()
            hay=self._terms(title+" "+summary)
            score=len(wanted & hay)
            out.append(WebCandidate(title[:240],link[:1500],summary[:1000],"web",score,bool(guard["suspicious"])))
        return out

    def scout(self, project, goal, limit=10):
        goal=str(goal or "").strip()
        if not goal: raise ValueError("Garuda requires a research goal")
        web_error=None; github_error=None; web=[]; repos=[]
        try:web=self._web(goal,limit)
        except Exception as exc:web_error=f"{type(exc).__name__}: {exc}"
        try:repos=(self.github.search(goal,limit).get("candidates") or [])
        except Exception as exc:github_error=f"{type(exc).__name__}: {exc}"
        wanted=self._terms(goal)
        for r in repos:
            r["fit_terms"]=len(wanted & self._terms((r.get("full_name") or "")+" "+(r.get("description") or "")))
        repos.sort(key=lambda x:(x.get("fit_terms",0),x.get("score",0),x.get("stars",0)),reverse=True)
        web.sort(key=lambda x:x.relevance,reverse=True)
        report={
            "agent":"Garuda","role":"read_only_discovery","project":project,"goal":goal,
            "web":[asdict(x) for x in web],"github":repos,
            "errors":{"web":web_error,"github":github_error},
            "handover":{
                "to":"KRISHNA","decision_authority":"KRISHNA",
                "auto_implementation":False,
                "required_before_implementation":["source review","license review","security review","dependency review","shadow integration","tests","browser/backend verification"]
            }
        }
        self.memory.remember(project,"garuda_research",goal,{"report":report})
        self.memory.audit("garuda_scout","completed",f"{project}:{len(web)} web:{len(repos)} github")
        return report
