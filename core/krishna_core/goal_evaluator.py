from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class GoalCheck:
    name: str
    passed: bool
    detail: str


class GoalEvaluator:
    """Concludes a project task against explicit acceptance criteria, not just absence of errors."""

    def evaluate(self, goal: str, checks: list[dict]) -> dict:
        results = [
            GoalCheck(
                name=str(item.get("name", "check")),
                passed=bool(item.get("passed")),
                detail=str(item.get("detail", "")),
            )
            for item in checks
        ]
        complete = bool(goal.strip()) and bool(results) and all(x.passed for x in results)
        return {
            "goal": goal,
            "complete": complete,
            "passed": sum(1 for x in results if x.passed),
            "failed": sum(1 for x in results if not x.passed),
            "checks": [asdict(x) for x in results],
            "conclusion": (
                "goal_verified_complete"
                if complete
                else "goal_not_yet_verified"
            ),
        }
