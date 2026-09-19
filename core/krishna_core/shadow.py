from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import os
import shutil
import subprocess
import tempfile
import time
import uuid


@dataclass
class ShadowWorkspace:
    workspace_id: str
    source: str
    path: str
    created_at: float


class ShadowWorkspaceManager:
    """SWE-ReX-inspired isolation boundary using local disposable copies.

    External SWE-ReX may later replace this backend without changing KRISHNA's API.
    """

    def __init__(self, root: str | None = None):
        self.root = Path(root or os.getenv(
            "KRISHNA_SHADOW_ROOT",
            str(Path(tempfile.gettempdir()) / "krishna-shadow"),
        ))
        self.root.mkdir(parents=True, exist_ok=True)

    def create(self, source: str) -> dict:
        src = Path(source).resolve()
        if not src.is_dir():
            raise ValueError("source must be a project directory")
        workspace_id = uuid.uuid4().hex
        dst = self.root / workspace_id
        ignore = shutil.ignore_patterns(".git", ".venv", "node_modules", "__pycache__", ".gradle", "build", "dist")
        shutil.copytree(src, dst, ignore=ignore)
        return asdict(ShadowWorkspace(workspace_id, str(src), str(dst), time.time()))

    def destroy(self, workspace_id: str) -> dict:
        dst = (self.root / workspace_id).resolve()
        if self.root.resolve() not in dst.parents:
            raise ValueError("invalid workspace")
        existed = dst.exists()
        if existed:
            shutil.rmtree(dst, ignore_errors=True)
        return {"destroyed": existed, "workspace_id": workspace_id}

    def run(self, workspace_id: str, argv: list[str], timeout: int = 300) -> dict:
        """Execute only an explicit argv array; never a shell string."""
        if not argv or not isinstance(argv, list):
            raise ValueError("argv list required")
        dst = (self.root / workspace_id).resolve()
        if self.root.resolve() not in dst.parents or not dst.is_dir():
            raise ValueError("unknown workspace")
        allowed = {
            "python", "python3", "pytest", "npm", "npx", "node", "gradle", "gradlew",
            "git", "ruff", "mypy", "cargo", "go", "java", "javac",
        }
        exe = Path(str(argv[0])).name.lower()
        if exe not in allowed:
            return {"ok": False, "blocked": True, "reason": f"executable not allowlisted: {exe}"}
        started = time.perf_counter()
        try:
            p = subprocess.run(
                [str(x) for x in argv],
                cwd=str(dst),
                capture_output=True,
                text=True,
                timeout=max(1, min(timeout, 1800)),
                shell=False,
            )
            return {
                "ok": p.returncode == 0,
                "returncode": p.returncode,
                "stdout": p.stdout[-30000:],
                "stderr": p.stderr[-20000:],
                "elapsed_ms": int((time.perf_counter() - started) * 1000),
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "timeout"}

    def tree_digest(self, workspace_id: str) -> str:
        dst = (self.root / workspace_id).resolve()
        h = hashlib.sha256()
        for path in sorted(p for p in dst.rglob("*") if p.is_file()):
            rel = path.relative_to(dst).as_posix()
            h.update(rel.encode())
            try:
                h.update(path.read_bytes())
            except OSError:
                pass
        return h.hexdigest()
