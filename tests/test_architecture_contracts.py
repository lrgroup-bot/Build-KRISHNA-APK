import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class ArchitectureContracts(unittest.TestCase):
    def text(self,p):return (ROOT/p).read_text(encoding="utf-8")
    def test_gyan_brain_identity(self):
        html=self.text("core/web_validation.html")
        self.assertIn("🧠",html); self.assertIn("Gyan-Bhandar",html)
    def test_commitment_recovery(self):
        o=self.text("core/krishna_core/orchestrator.py"); s=self.text("core/krishna_core/server.py")
        self.assertIn("resume_unfinished_work",o);self.assertIn("/api/commitments/resume",s)
    def test_kabach_project_boundary(self):
        k=self.text("core/krishna_core/kabach.py");s=self.text("core/krishna_core/server.py")
        for x in ("egress_default_deny","secret_in_payload","protect_project","gate_external_evidence"):self.assertIn(x,k)
        self.assertIn("/api/kabach/projects",s)
    def test_model_pool(self):
        r=self.text("core/krishna_core/router.py")
        for x in ("openai","anthropic","gemini","xai","openrouter","ollama"):self.assertIn(x,r)
        self.assertIn("coding_plan",r)
    def test_factory_organization_contract(self):
        sf=self.text("core/krishna_core/software_factory.py");o=self.text("core/krishna_core/orchestrator.py");s=self.text("core/krishna_core/server.py")
        for x in ("worker_request","test_plan","route_defect","suggested_worker_count","actual timestamps"):self.assertIn(x,sf)
        for x in ("EphemeralWorkerRuntime","testing_lead_live_verify","gyan_bhandar.store"):self.assertIn(x,o)
        for x in ("/api/software-factory/hr","/api/software-factory/test-plan","/api/software-factory/testing-lead/verify"):self.assertIn(x,s)
    def test_ephemeral_worker_contract(self):
        e=self.text("core/krishna_core/ephemeral_workers.py")
        for x in ("KRISHNA approval required","ThreadPoolExecutor","destroyed","max_workers"):self.assertIn(x,e)
    def test_browser_testing_lead_contract(self):
        b=self.text("core/krishna_core/browser_operator.py")
        self.assertIn("exhaustive_clickthrough",b);self.assertIn("controls_checked",b)
    def test_garuda_security_delegation(self):
        o=self.text("core/krishna_core/orchestrator.py")
        self.assertIn("kabach_security_research",o);self.assertIn("self.garuda.scout",o)

if __name__=="__main__":unittest.main()
