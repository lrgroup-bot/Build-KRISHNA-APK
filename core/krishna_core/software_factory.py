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
    def plan(self,project,goal,deadline_hours=None,start_at=None,end_at=None):
        now=time.time(); pid=str(uuid.uuid4())
        start=float(start_at or now)
        if end_at is not None:
            deadline_hours=max(0.0,(float(end_at)-start)/3600.0)
        deadline_at=None if deadline_hours is None else start+float(deadline_hours)*3600
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
            target=start+float(deadline_hours)*(5/6)*3600
        result={"factory_id":pid,"project":project,"goal":goal,"stages":self.STAGES,"teams":{k:[vars(x) for x in v] for k,v in teams.items()},"deadline_hours":deadline_hours,"start_at":start,"deadline_at":deadline_at,"internal_target_at":target,"rules":{"failed_gate":"return_to_responsible_team","coding_manager":"requests ephemeral coder workers from KRISHNA; cannot spawn directly","test_manager":"chooses automated/manual/both and requests ephemeral tester workers from KRISHNA; cannot spawn directly","testing_lead":"live click-through and result verification; defects return to engineering unless safely repairable within assigned scope","project_manager":"final acceptance","hr":"owns timeline calculation and measured workload; advises managers how many workers/time remain; managers request workers from KRISHNA","system_engineering":"handles approved additions/change requests","authority":"KRISHNA"}}
        if self.commitments:self.commitments.add(project,"Deliver project through Software Factory",result,"KRISHNA","planned")
        self.memory.remember(project,"software_factory_plan",goal,result)
        return result
    def worker_request(self,project,manager,role,count,reason,hr_snapshot,approved_by_krishna=False):
        count=max(0,int(count)); manager=str(manager or "").strip()
        if count<1:raise ValueError("worker count must be positive")
        req={"request_id":str(uuid.uuid4()),"project":project,"manager":manager,"role":role,"requested_count":count,"reason":reason,"hr_snapshot":hr_snapshot or {},"approved_by":"KRISHNA" if approved_by_krishna else None,"status":"approved" if approved_by_krishna else "waiting_krishna_approval","ephemeral":True,"created_at":time.time()}
        self.memory.remember(project,"ephemeral_worker_request",reason,req)
        return req

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
    def test_plan(self,project_type="web",risk="medium",has_ui=True,has_api=True):
        risk=str(risk).lower(); checks=["unit","regression"]
        if has_api: checks+=["api","integration"]
        if has_ui: checks+=["browser","manual_clickthrough","visual"]
        if risk in {"high","critical"}: checks+=["security","rollback","recovery","performance"]
        return {"project_type":project_type,"risk":risk,"mode":"both" if has_ui else "automated","checks":list(dict.fromkeys(checks)),"owner":"testing_manager","final_live_verifier":"testing_lead"}

    def route_defect(self,defect):
        text=str(defect or "").lower()
        if any(x in text for x in ("security","secret","auth","permission","vulnerability")): return "system_engineering"
        if any(x in text for x in ("test","flaky","fixture")): return "testing"
        return "engineering"

    def hr_status(self,project,workers,deadline_at=None,total_units=None,completed_units=None):
        now=time.time(); rows=[]
        for w in workers:
            started=float(w.get("assigned_at") or now); ended=float(w.get("ended_at") or now)
            rows.append({**w,"worked_seconds":max(0,ended-started)})
        remaining=None if not deadline_at else float(deadline_at)-now
        total=max(0,float(total_units or 0)); done=max(0,float(completed_units or 0))
        progress=(done/total) if total else None; elapsed=sum(x["worked_seconds"] for x in rows)
        rate=(done/elapsed) if done and elapsed else None
        eta=((total-done)/rate) if rate and total>=done else None
        risk=bool(remaining is not None and (remaining<0 or (eta is not None and eta>max(0,remaining))))
        suggested=1
        if remaining and remaining>0 and rate and total>done: suggested=max(1,int(((total-done)/(rate*remaining))+0.999))
        return {"project":project,"workers":rows,"deadline_remaining_seconds":remaining,"progress":progress,"measured_rate_units_per_second":rate,"forecast_eta_seconds":eta,"deadline_risk":risk,"staffing_action":"request_scale_up" if risk else "monitor","suggested_worker_count":suggested,"measurement_policy":"actual timestamps and completed work only; never fabricate productivity"}
