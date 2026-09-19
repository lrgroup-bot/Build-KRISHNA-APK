from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Callable, Iterable
import time


@dataclass
class VerificationResult:
    name: str
    passed: bool
    detail: str
    elapsed_ms: int


class VerificationEngine:
    """Mandatory evidence-based gate before KRISHNA marks work as verified."""

    def run(self, checks: Iterable[tuple[str, Callable[[], tuple[bool, str]]]]) -> dict:
        results = []
        for name, fn in checks:
            started = time.perf_counter()
            try:
                ok, detail = fn()
                passed = bool(ok)
            except Exception as exc:
                passed = False
                detail = f"{type(exc).__name__}: {exc}"
            elapsed = int((time.perf_counter() - started) * 1000)
            results.append(VerificationResult(name, passed, str(detail), elapsed))

        passed = bool(results) and all(r.passed for r in results)
        return {
            "verified": passed,
            "checks": [asdict(r) for r in results],
            "passed": sum(1 for r in results if r.passed),
            "failed": sum(1 for r in results if not r.passed),
        }
