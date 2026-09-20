from __future__ import annotations
from collections import Counter
import re, time

class GyanBhandarAgent:
    """Evidence-backed knowledge curator. Stores and strengthens theory; KRISHNA remains decision authority."""
    def __init__(self, memory, garuda):
        self.memory=memory; self.garuda=garuda

    @staticmethod
    def _terms(text):
        return {x for x in re.findall(r"[a-z0-9][a-z0-9_+.-]{2,}",str(text).lower()) if len(x)>2}

    def store(self, project, topic, lesson, evidence=None, confidence=0.0, source="sudarshan", verified=False):
        item=self.memory.learn(project,topic,lesson,evidence or [],confidence,source,verified)
        self.memory.audit("gyan_bhandar_store","verified" if verified else "candidate",f"{project}:{item['fingerprint']}")
        return item

    def recall(self, project, topic=None, limit=50, verified_only=False):
        rows=self.memory.learnings(project,limit,verified_only)
        if topic:
            wanted=self._terms(topic)
            rows.sort(key=lambda x:len(wanted & self._terms(x["topic"]+" "+x["lesson"])),reverse=True)
        return rows

    def strengthen(self, project, topic, use_garuda=True, limit=10):
        existing=self.recall(project,topic,limit=50)
        research=None
        if use_garuda:
            research=self.garuda.scout(project,f"{topic} architecture implementation theory evidence alternatives risks",limit)
        source_counts=Counter()
        evidence=[]
        if research:
            for row in research.get("web",[]):
                if not row.get("suspicious"):
                    source_counts[row.get("source","web")]+=1
                    evidence.append({"title":row.get("title"),"url":row.get("url"),"source":row.get("source"),"fingerprint":row.get("fingerprint")})
            for row in research.get("github",[]):
                source_counts["github"]+=1
                evidence.append({"repository":row.get("full_name"),"url":row.get("html_url") or row.get("url"),"source":"github"})
        result={
            "agent":"Gyan-Bhandar","project":project,"topic":topic,
            "existing_learnings":existing,
            "new_evidence":evidence[:max(10,limit*3)],
            "source_diversity":dict(source_counts),
            "theory_status":"evidence_collected" if evidence else "memory_only",
            "handover":{
                "to":"KRISHNA","decision_authority":"KRISHNA","auto_implementation":False,
                "implementation_executor":"Sudarshan",
                "required_before_use":["compare existing learning","inspect evidence","identify contradictions","form implementation theory","verify in shadow/tests"]
            },
            "created_at":time.time()
        }
        self.memory.remember(project,"gyan_bhandar_analysis",topic,{"analysis":result})
        self.memory.audit("gyan_bhandar_strengthen","completed",f"{project}:{topic}:{len(evidence)} evidence")
        return result
