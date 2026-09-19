from __future__ import annotations

from dataclasses import dataclass, asdict
import time
import uuid

from .integrations import IntegrationRegistry
from .shadow import ShadowWorkspaceManager


@dataclass
class AgentStep:
    index: int
    action: list[str]
    ok: bool
    result: dict


class EngineeringWorker:
    """mini-SWE-inspired linear worker operating only inside a shadow workspace.

    The planner supplies explicit argv actions. This deliberately does not convert
    arbitrary natural language directly into shell commands.
    """

    def __init__(self, shadows: ShadowWorkspaceManager):
        self.shadows = shadows

    def execute_plan(self, source: str, actions: list[list[str]], max_steps: int = 20) -> dict:
        if len(actions) > max_steps:
            raise ValueError("plan exceeds maximum step count")
        ws = self.shadows.create(source)
        steps = []
        started = time.time()
        try:
            for idx, action in enumerate(actions):
                result = self.shadows.run(ws["workspace_id"], action)
                steps.append(asdict(AgentStep(idx, action, bool(result.get("ok")), result)))
                if not result.get("ok"):
                    break
            return {
                "run_id": uuid.uuid4().hex,
                "workspace": ws,
                "steps": steps,
                "all_passed": bool(steps) and all(s["ok"] for s in steps),
                "elapsed_seconds": round(time.time() - started, 3),
                "final_digest": self.shadows.tree_digest(ws["workspace_id"]),
            }
        except Exception:
            self.shadows.destroy(ws["workspace_id"])
            raise


class ExtensionBus:
    """Goose-inspired provider/MCP-style capability registry without coupling KRISHNA to Goose."""

    def __init__(self, integrations: IntegrationRegistry):
        self.integrations = integrations

    def status(self) -> dict:
        return {
            "goose_available": self.integrations.available("goose"),
            "external_tools": self.integrations.statuses(),
            "design": "KRISHNA owns identity, policy, memory and verification; extensions are replaceable",
        }
