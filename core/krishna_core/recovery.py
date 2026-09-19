from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Callable, Dict, List
import time


@dataclass
class RecoveryStep:
    level: int
    name: str
    safe_automatic: bool
    description: str


DEFAULT_LADDER = [
    RecoveryStep(0, "observe", True, "Collect health and runtime evidence."),
    RecoveryStep(1, "retry", True, "Retry the failed operation without changing state."),
    RecoveryStep(2, "restart_component", True, "Restart only a registered component."),
    RecoveryStep(3, "restore_config", False, "Restore a known-good registered configuration."),
    RecoveryStep(4, "known_repair", False, "Apply a previously verified repair pattern."),
    RecoveryStep(5, "investigate", True, "Run evidence and hypothesis investigation."),
    RecoveryStep(6, "generate_patch", False, "Prepare a bounded code/configuration patch."),
    RecoveryStep(7, "shadow_test", True, "Test in an isolated or non-production workspace."),
    RecoveryStep(8, "deploy", False, "Promote only after verification passes."),
    RecoveryStep(9, "rollback", True, "Restore the last known-good state on failed verification."),
]


class RecoveryEngine:
    """Policy-driven recovery ladder. Actions must be pre-registered callables."""

    def __init__(self, allow_mutating_actions: bool = False):
        self.allow_mutating_actions = allow_mutating_actions
        self.actions: Dict[str, Callable[[dict], dict]] = {}

    def register(self, name: str, fn: Callable[[dict], dict]) -> None:
        self.actions[name] = fn

    def ladder(self) -> List[dict]:
        return [asdict(step) for step in DEFAULT_LADDER]

    def execute(self, step_name: str, payload: dict | None = None) -> dict:
        step = next((s for s in DEFAULT_LADDER if s.name == step_name), None)
        if not step:
            raise KeyError(step_name)
        if not step.safe_automatic and not self.allow_mutating_actions:
            return {
                "executed": False,
                "blocked": True,
                "reason": "mutating recovery actions disabled by policy",
                "step": asdict(step),
            }
        action = self.actions.get(step_name)
        if not action:
            return {
                "executed": False,
                "blocked": False,
                "reason": "no registered action",
                "step": asdict(step),
            }
        started = time.time()
        result = action(payload or {})
        return {
            "executed": True,
            "step": asdict(step),
            "result": result,
            "elapsed_seconds": round(time.time() - started, 3),
        }
