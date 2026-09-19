from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import shutil
import tempfile
import time


@dataclass
class ShadowWorkspace:
    source: str
    path: str
    created_at: float


class ShadowWorkspaceManager:
    """Creates disposable local copies so repairs can be tested before promotion."""

    def __init__(self, base_dir: str | None = None):
        self.base_dir = base_dir

    def create(self, source: str | Path) -> dict:
        source = Path(source).resolve()
        if not source.is_dir():
            raise ValueError("source project root must be a directory")
        target = Path(tempfile.mkdtemp(prefix="krishna-shadow-", dir=self.base_dir))
        work = target / "workspace"
        shutil.copytree(
            source,
            work,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"),
        )
        return asdict(ShadowWorkspace(str(source), str(work), time.time()))

    def destroy(self, workspace_path: str | Path) -> bool:
        p = Path(workspace_path).resolve()
        parent = p.parent
        if not parent.name.startswith("krishna-shadow-"):
            raise ValueError("refusing to delete non-shadow path")
        shutil.rmtree(parent, ignore_errors=False)
        return True
