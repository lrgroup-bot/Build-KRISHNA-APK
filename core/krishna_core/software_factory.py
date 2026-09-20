from __future__ import annotations
import time,uuid
from dataclasses import dataclass,field

@dataclass
class Worker:
    role:str; team:str; specialty:str; status:str="available"; assigned_at:float=0.0

class SoftwareFactory:
    """KRISHNA-governed hierarchical software delivery pipeline."""
    STAGES=("engineering","lead_review","coding_manager","testing","testing_lead","project_manager","handover")
    def __init__(self,memory,commitments=None):
        self.memory=memory;self.commitments=commitments
    def plan(self,project,goal,deadline_hours=None):
        now=time.time(); pid=str(uuid.uuid4())
        teams={
          "engineering":[Worker("frontend_developer","engineering","GUI/UX/browser"),Worker("backend_developer","engineering","backend/API/integration")],
          "lead_review":[Worker("engineering_lead","lead","code+GUI review")],
          "coding_manager":[Worker("coding_manager","management","whole-project engineering review and staffing")],
          "testing":[Worker("test_manager","testing","test strategy and staffing"),Worker("automation_tester","testing","automated regression"),Worker("manual_tester","testing","interactive/manual checks")],
          "testing_lead":[Worker("testing_lead","quality","live end-to-end UI/API verification and defect triage")],
          "project_manager":[Worker("project_manager","management","final acceptance and handover")],
          "system_engineering":[Worker("system_engineer","systems","post-build additions/infrastructure/integration")],
          "hr":[Worker("hr_manager","operations","workload, staffing, time and delivery monitoring")],
        }
        target=None
        if deadline_hours:
            # internal target leaves a 1/6 delivery buffer; e.g. 72h -> 60h (2.5 days)
            target=now+float(deadline_hours)*(5/6)*3600
        result={"factory_id":pid,"project":project,"goal":goal,"stages":self.STAGES,"teams":{k:[vars(x) for x in v] for k,v in teams.items()},"deadline_hours":deadline_hours,"internal_target_at":target,"rules":{"failed_gate":"return_to_responsible_team","coding_manager":"may_scale_coder_workers","test_manager":"chooses automated/manual/both based on project risk and interfaces","testing_lead":"live click-through and result verification; defects return to engineering unless safely repairable within assigned scope","project_manager":"final acceptance","hr":"tracks real measured work and deadline risk; may request more workers","system_engineering":"handles approved additions/change requests","authority":"KRISHNA"}}
        if self.commitments:self.commitments.add(project,"Deliver project through Software Factory",result,"KRISHNA","planned")
        self.memory.remember(project,"software_factory_plan",goal,result)
        return result
    def gate(self,project,stage,passed,evidence=None,defects=None):
        if stage not in self.STAGES:raise ValueError("invalid stage")
        evidence=evidence or []; defects=defects or []
        if passed and not evidence:raise ValueError("a pass requires verification evidence")
        nxt=None
        if passed:
            i=self.STAGES.index(stage);nxt=self.STAGES[i+1] if i+1<len(self.STAGES) else "completed"
        else:nxt="engineering"
        record={"stage":stage,"passed":bool(passed),"evidence":evidence,"defects":defects,"next":nxt,"at":time.time()}
        self.memory.remember(project,"software_factory_gate",stage,record)
        return record
    def hr_status(self,project,workers,deadline_at=None):
        now=time.time(); rows=[]
        for w in workers:
            started=float(w.get("assigned_at") or now); ended=float(w.get("ended_at") or now)
            rows.append({**w,"worked_seconds":max(0,ended-started)})
        remaining=None if not deadline_at else float(deadline_at)-now
        return {"project":project,"workers":rows,"deadline_remaining_seconds":remaining,"deadline_risk":remaining is not None and remaining<0,"staffing_action":"request_scale_up" if remaining is not None and remaining<0 else "monitor"}
