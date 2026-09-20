from __future__ import annotations
from collections import Counter
from urllib.parse import urlparse
import re, time, uuid, hashlib, json, zlib
from pathlib import Path

class GyanBhandarAgent:
    """Evidence-backed knowledge curator. Stores and strengthens theory; KRISHNA remains decision authority."""
    def __init__(self, memory, garuda):
        self.memory=memory; self.garuda=garuda
        state=Path(self.memory.db.execute("PRAGMA database_list").fetchone()[2]).resolve().parent/".krishna_state"
        self.archive_root=state/"gyan_archive"; self.archive_root.mkdir(parents=True,exist_ok=True)
        self.archive_index=self.archive_root/"index.jsonl"

    def archive_file(self, project, source_path, topic="", remove_original=False):
        src=Path(source_path).resolve()
        if not src.is_file():raise FileNotFoundError(str(src))
        raw=src.read_bytes(); digest=hashlib.sha256(raw).hexdigest()
        target=self.archive_root/(digest+".zlib")
        deduplicated=target.exists()
        if not deduplicated:target.write_bytes(zlib.compress(raw,9))
        record={"sha256":digest,"project":project,"topic":str(topic or src.name)[:240],"name":src.name,
            "original_bytes":len(raw),"archive_bytes":target.stat().st_size,"archive":str(target),
            "compression":"zlib-9","created_at":time.time(),"deduplicated":deduplicated}
        with self.archive_index.open("a",encoding="utf-8") as h:h.write(json.dumps(record,separators=(",",":"))+"\n")
        if remove_original:src.unlink()
        self.memory.audit("gyan_file_archive","completed",f"{project}:{digest}:{record['original_bytes']}->{record['archive_bytes']}")
        return {k:v for k,v in record.items() if k!="archive"}

    def restore_file(self, sha256, destination):
        digest=str(sha256).lower().strip()
        if not re.fullmatch(r"[0-9a-f]{64}",digest):raise ValueError("invalid sha256")
        src=self.archive_root/(digest+".zlib")
        if not src.is_file():raise FileNotFoundError(digest)
        raw=zlib.decompress(src.read_bytes())
        if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError("archive integrity check failed")
        dst=Path(destination).resolve(); dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes(raw)
        return {"sha256":digest,"destination":str(dst),"bytes":len(raw),"verified":True}

    def archive_status(self):
        files=list(self.archive_root.glob("*.zlib"))
        return {"agent":"Gyan-Bhandar","files":len(files),"compressed_bytes":sum(x.stat().st_size for x in files),
            "policy":"content-addressed SHA-256 archive; duplicate files stored once; originals are retained unless explicit removal is requested"}

    @staticmethod
    def _terms(text):
        return {x for x in re.findall(r"[a-z0-9][a-z0-9_+.-]{2,}",str(text).lower()) if len(x)>2}

    def store(self, project, topic, lesson, evidence=None, confidence=0.0, source="sudarshan", verified=False):
        item=self.memory.learn(project,topic,lesson,evidence or [],confidence,source,verified)
        self.memory.audit("gyan_bhandar_store","verified" if verified else "candidate",f"{project}:{item['fingerprint']}")
        return item

    def propose(self, project, topic, lesson, evidence=None, confidence=0.0, source="research", verified=False):
        approval_id=str(uuid.uuid4())
        item=self.memory.create_gyan_pending(approval_id,project,topic,lesson,evidence or [],confidence,source,verified)
        self.memory.audit("gyan_bhandar_proposal","waiting_approval",f"{project}:{approval_id}:{topic}")
        return {**item,"stored":False,"requires_user_approval":True,
            "question":"Save these findings to Gyan-Bhandar?"}

    def pending(self, project=None, limit=100):
        return self.memory.list_gyan_pending(project,"pending",limit)

    def decide(self, approval_id, approved):
        item=self.memory.gyan_pending(approval_id)
        if not item or item.get("status")!="pending":raise KeyError(approval_id)
        if not approved:
            out=self.memory.decide_gyan_pending(approval_id,"rejected")
            self.memory.audit("gyan_bhandar_proposal","rejected",approval_id)
            return {**out,"stored":False}
        stored=self.store(item["project"],item["topic"],item["lesson"],item["evidence"],item["confidence"],item["source"],item["verified"])
        out=self.memory.decide_gyan_pending(approval_id,"approved")
        self.memory.audit("gyan_bhandar_proposal","approved",approval_id)
        return {**out,"stored":True,"learning":stored}

    def compact_storage(self):
        result=self.memory.compact_gyan_storage()
        self.memory.audit("gyan_bhandar_compact","completed",f"{result['records_compacted']} records; {result['bytes_saved']} bytes saved")
        return {"agent":"Gyan-Bhandar",**result}

    def recall(self, project, topic=None, limit=50, verified_only=False):
        rows=self.memory.learnings(project,limit,verified_only)
        if topic:
            wanted=self._terms(topic)
            rows.sort(key=lambda x:len(wanted & self._terms(x["topic"]+" "+x["lesson"])),reverse=True)
        return rows

    def theory(self, project, topic, limit=25):
        rows=self.recall(project,topic,limit=limit)
        verified=[x for x in rows if x.get("status")=="verified"]
        candidates=[x for x in rows if x.get("status")!="verified"]
        evidence=[]; domains=Counter()
        for row in rows:
            for ev in row.get("evidence") or []:
                if isinstance(ev,dict):
                    u=str(ev.get("url") or "")
                    if u:
                        domains[urlparse(u).netloc or "local"]+=1
                    evidence.append(ev)
        return {"agent":"Gyan-Bhandar","project":project,"topic":topic,
            "theory":{"verified_lessons":[x["lesson"] for x in verified[:8]],"candidate_lessons":[x["lesson"] for x in candidates[:8]],
                "implementation_rule":"Verified lessons may inform KRISHNA decisions; candidate lessons require evidence or tests before promotion.",
                "evidence_count":len(evidence),"independent_domains":len(domains),"domains":dict(domains)},
            "decision_authority":"KRISHNA","implementation_executor":"Sudarshan"}

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
            "current_theory":self.theory(project,topic,limit=50),
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
