from __future__ import annotations

import time
import uuid

from .change_gate import ChangeGate
from .code_intelligence import CodeIntelligence
from .operator import ComputerOperator
from .agent_runtime import EngineeringWorker, ExtensionBus
from .shadow import ShadowWorkspaceManager
from .integrations import IntegrationRegistry


class MythosEngineeringStack:
    """KRISHNA's integrated Mythos-style engineering capability layer."""

    def __init__(self, memory, investigator, verifier):
        self.memory = memory
        self.investigator = investigator
        self.verifier = verifier
        self.integrations = IntegrationRegistry()
        self.code = CodeIntelligence(self.integrations)
        self.gate = ChangeGate()
        self.shadows = ShadowWorkspaceManager()
        self.worker = EngineeringWorker(self.shadows)
        self.operator = ComputerOperator(self.integrations)
        self.extensions = ExtensionBus(self.integrations)

    def status(self) -> dict:
        return {
            "name": "KRISHNA Mythos Engineering Stack",
            "operating_loop": [
                "recon", "hypothesis", "evidence", "change_gate",
                "shadow_execute", "test", "visual_verify", "verify", "learn",
            ],
            "integrations": self.integrations.statuses(),
            "computer_operator": self.operator.status(),
            "extensions": self.extensions.status(),
        }

    def recon(self, project: str, project_path: str, symptom: str, components=None) -> dict:
        report = {
            "recon_id": uuid.uuid4().hex,
            "project": project,
            "project_path": project_path,
            "symptom": symptom,
            "code_intelligence": self.code.status(project_path),
            "external_security": {
                "backend": "mythos-agent",
                "available": self.integrations.available("mythos_agent"),
                "mode": "defensive only",
            },
            "created_at": time.time(),
        }
        self.memory.remember(project, "engineering_recon", symptom, report)
        return report

    def assess_change(self, **kwargs) -> dict:
        return self.gate.assess(**kwargs)

    def run_shadow_plan(self, project: str, source: str, actions: list[list[str]]) -> dict:
        result = self.worker.execute_plan(source, actions)
        self.memory.remember(project, "shadow_run", source, {
            "run_id": result["run_id"],
            "all_passed": result["all_passed"],
            "final_digest": result["final_digest"],
        })
        return result
