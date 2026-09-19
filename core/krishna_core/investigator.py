from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Callable, Dict, Iterable, List
import time
import uuid


@dataclass
class Evidence:
    source: str
    kind: str
    detail: str
    confidence: float = 1.0
    observed_at: float = field(default_factory=time.time)


@dataclass
class Hypothesis:
    statement: str
    confidence: float
    supporting_sources: List[str] = field(default_factory=list)
    conflicting_sources: List[str] = field(default_factory=list)
    status: str = "untested"


class EvidenceEngine:
    """Collects registered safe probes. No natural-language shell execution."""

    def __init__(self):
        self._probes: Dict[str, Callable[[dict], Iterable[Evidence]]] = {}

    def register_probe(self, name: str, probe: Callable[[dict], Iterable[Evidence]]) -> None:
        self._probes[name] = probe

    def collect(self, context: dict, selected: List[str] | None = None) -> List[Evidence]:
        names = selected or sorted(self._probes)
        evidence: List[Evidence] = []
        for name in names:
            probe = self._probes.get(name)
            if not probe:
                continue
            try:
                evidence.extend(list(probe(context)))
            except Exception as exc:
                evidence.append(Evidence(
                    source=name,
                    kind="probe_error",
                    detail=f"{type(exc).__name__}: {exc}",
                    confidence=1.0,
                ))
        return evidence


class InvestigationEngine:
    """Mythos-inspired evidence -> hypothesis -> verification workflow."""

    def __init__(self, evidence_engine: EvidenceEngine | None = None):
        self.evidence_engine = evidence_engine or EvidenceEngine()

    def investigate(
        self,
        symptom: str,
        context: dict | None = None,
        hypothesis_builder: Callable[[str, List[Evidence], dict], List[Hypothesis]] | None = None,
    ) -> dict:
        context = context or {}
        investigation_id = str(uuid.uuid4())
        evidence = self.evidence_engine.collect(context)
        if hypothesis_builder:
            hypotheses = hypothesis_builder(symptom, evidence, context)
        else:
            hypotheses = self._baseline_hypotheses(symptom, evidence)

        hypotheses = sorted(hypotheses, key=lambda h: h.confidence, reverse=True)
        return {
            "investigation_id": investigation_id,
            "symptom": symptom,
            "evidence": [asdict(e) for e in evidence],
            "hypotheses": [asdict(h) for h in hypotheses],
            "status": "evidence_collected" if evidence else "needs_evidence",
            "created_at": time.time(),
        }

    @staticmethod
    def _baseline_hypotheses(symptom: str, evidence: List[Evidence]) -> List[Hypothesis]:
        low = symptom.lower()
        source_names = [e.source for e in evidence]
        guesses: List[Hypothesis] = []
        if any(x in low for x in ("timeout", "connection", "unreachable", "refused")):
            guesses.append(Hypothesis(
                "service or network dependency unavailable",
                0.55,
                supporting_sources=source_names,
            ))
        if any(x in low for x in ("500", "exception", "traceback", "error")):
            guesses.append(Hypothesis(
                "application runtime failure",
                0.50,
                supporting_sources=source_names,
            ))
        if any(x in low for x in ("config", "env", "path", "missing")):
            guesses.append(Hypothesis(
                "configuration or dependency path mismatch",
                0.45,
                supporting_sources=source_names,
            ))
        if not guesses:
            guesses.append(Hypothesis(
                "insufficient evidence; gather runtime, logs, dependency and recent-change evidence",
                0.20,
                supporting_sources=source_names,
            ))
        return guesses
