from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from threading import RLock
from typing import Dict, List
import os


@dataclass
class ProjectPolicy:
    name: str
    root: str
    privacy: str = "local_only"
    allowed_actions: List[str] = field(default_factory=list)
    verification_checks: List[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def normalized(self) -> "ProjectPolicy":
        root = str(Path(os.path.expandvars(os.path.expanduser(self.root))).resolve())
        return ProjectPolicy(
            name=self.name.strip(),
            root=root,
            privacy=self.privacy,
            allowed_actions=sorted(set(self.allowed_actions)),
            verification_checks=sorted(set(self.verification_checks)),
            metadata=dict(self.metadata),
        )


class ProjectRegistry:
    """Local registry of projects KRISHNA is explicitly allowed to inspect/manage."""

    def __init__(self):
        self._lock = RLock()
        self._projects: Dict[str, ProjectPolicy] = {}

    def register(self, project: ProjectPolicy) -> dict:
        project = project.normalized()
        if not project.name:
            raise ValueError("project name is required")
        if project.privacy not in {"local_only", "approved_cloud", "restricted"}:
            raise ValueError("invalid privacy profile")
        with self._lock:
            self._projects[project.name] = project
        return asdict(project)

    def get(self, name: str) -> ProjectPolicy | None:
        with self._lock:
            return self._projects.get(name)

    def list(self) -> List[dict]:
        with self._lock:
            return [asdict(self._projects[k]) for k in sorted(self._projects)]

    def can(self, name: str, action: str) -> bool:
        project = self.get(name)
        return bool(project and action in project.allowed_actions)

    def path_for(self, name: str) -> Path:
        project = self.get(name)
        if not project:
            raise KeyError(name)
        return Path(project.root)
