from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib


@dataclass
class ChangeDecision:
    allowed: bool
    risk: str
    reasons: list[str]
    required_checks: list[str]


class ChangeGate:
    """CALM-inspired hard pre-write gate for KRISHNA-owned projects."""

    HIGH_RISK_NAMES = {
        "auth", "security", "payment", "trade", "order", "database",
        "migration", "config", "deploy", "router", "permission", "secret",
    }

    def file_hash(self, path: str) -> str:
        data = Path(path).read_bytes()
        return hashlib.sha256(data).hexdigest()

    def assess(
        self,
        path: str,
        expected_hash: str | None = None,
        caller_count: int = 0,
        changed_lines: int = 0,
        tests_present: bool = False,
        external_risk: str | None = None,
        explicit_confirmation: bool = False,
    ) -> dict:
        p = Path(path)
        reasons: list[str] = []
        required = ["shadow_workspace", "syntax_or_compile_check", "verification_gate"]
        risk_score = 0

        if not p.exists() or not p.is_file():
            return asdict(ChangeDecision(False, "critical", ["target file does not exist"], required))

        if expected_hash and self.file_hash(path) != expected_hash:
            return asdict(ChangeDecision(False, "critical", ["file changed since evidence was collected"], required))

        low_name = p.name.lower()
        if any(word in low_name for word in self.HIGH_RISK_NAMES):
            risk_score += 2
            reasons.append("sensitive file category")
        if caller_count >= 10:
            risk_score += 2
            reasons.append(f"high fan-in ({caller_count} callers)")
        elif caller_count >= 3:
            risk_score += 1
            reasons.append(f"multiple callers ({caller_count})")
        if changed_lines >= 100:
            risk_score += 2
            reasons.append("large patch")
        elif changed_lines >= 30:
            risk_score += 1
            reasons.append("medium patch")
        if external_risk in {"high", "critical"}:
            risk_score += 2
            reasons.append(f"external graph risk: {external_risk}")
        if not tests_present:
            risk_score += 1
            reasons.append("no directly-associated test evidence")
            required.append("add_or_run_regression_test")

        risk = "low" if risk_score <= 1 else "medium" if risk_score <= 3 else "high"
        if risk == "high":
            required.extend(["caller_impact_review", "explicit_confirmation"])
            if not explicit_confirmation:
                reasons.append("high-risk write requires explicit confirmation")
                return asdict(ChangeDecision(False, risk, reasons, sorted(set(required))))

        return asdict(ChangeDecision(True, risk, reasons or ["bounded change"], sorted(set(required))))
