from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Callable

from .shadow_workspace import ShadowWorkspaceManager


class RepairAgent:
    """Evidence-first shadow repair workflow with mandatory verification."""

    def __init__(self, investigator, verifier, memory, governor,
                 shadow: ShadowWorkspaceManager | None = None, candidate_root: str | Path | None = None):
        self.investigator = investigator
        self.verifier = verifier
        self.memory = memory
        self.governor = governor
        self.shadow = shadow or ShadowWorkspaceManager()
        self.candidate_root = Path(candidate_root).resolve() if candidate_root else None
        if self.candidate_root:
            self.candidate_root.mkdir(parents=True, exist_ok=True)

    def run(self, project: str, project_root: str, symptom: str,
            patcher: Callable[[Path, dict], dict],
            checks_factory: Callable[[Path], list[tuple[str, Callable[[], tuple[bool, str]]]]],
            components: list[str] | None = None) -> dict:
        repair_id = str(uuid.uuid4())
        started = time.time()
        with self.governor.job(timeout=0):
            investigation = self.investigator(symptom, project, components or [])
            workspace = self.shadow.create(project_root)
            work_path = Path(workspace["path"])
            try:
                patch = patcher(work_path, investigation)
                verification = self.verifier.run(checks_factory(work_path))
                status = "verified" if verification["verified"] else "rejected"
                self.memory.save_incident(
                    investigation["investigation_id"],
                    project,
                    symptom,
                    status=status,
                    root_cause=(investigation.get("hypotheses") or [{}])[0].get("statement", ""),
                    repair=str(patch),
                    verification=verification,
                )
                candidate_path = None
                if verification["verified"] and self.candidate_root:
                    candidate_path = self.candidate_root / repair_id
                    if candidate_path.exists():
                        import shutil
                        shutil.rmtree(candidate_path)
                    import shutil
                    shutil.copytree(work_path, candidate_path)
                self.memory.audit(repair_id, status, f"{project}:{symptom}")
                return {
                    "repair_id": repair_id,
                    "project": project,
                    "status": status,
                    "promotable": bool(verification["verified"]),
                    "candidate_root": str(candidate_path) if candidate_path else None,
                    "investigation": investigation,
                    "patch": patch,
                    "verification": verification,
                    "elapsed_seconds": round(time.time() - started, 3),
                }
            finally:
                self.shadow.destroy(work_path)
