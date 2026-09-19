from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import os
import shutil
import subprocess
from typing import Dict, List


@dataclass
class ToolStatus:
    name: str
    command: str
    available: bool
    purpose: str
    license: str
    optional: bool = True


class IntegrationRegistry:
    """Capability registry for external Mythos-style tools.

    KRISHNA owns orchestration/policy. External projects remain replaceable adapters.
    """

    DEFAULTS = {
        "codebase_memory": ("codebase-memory-mcp", "repository graph / impact analysis", "MIT"),
        "calm": ("calm", "live code graph and guarded writes", "MIT"),
        "mythos_agent": ("mythos-agent", "defensive recon / hypothesis security analysis", "MIT"),
        "mini_swe": ("mini", "minimal autonomous software-engineering worker", "MIT"),
        "swe_rex": ("swe-rex", "sandboxed execution backend", "MIT"),
        "arise": ("arise", "Python data-flow slicing / fault localization", "MIT"),
        "cua": ("cua", "computer-use driver", "MIT"),
        "goose": ("goose", "MCP/provider/agent extension worker", "Apache-2.0"),
    }

    ENV_OVERRIDES = {
        "codebase_memory": "KRISHNA_CODEBASE_MEMORY_CMD",
        "calm": "KRISHNA_CALM_CMD",
        "mythos_agent": "KRISHNA_MYTHOS_AGENT_CMD",
        "mini_swe": "KRISHNA_MINI_SWE_CMD",
        "swe_rex": "KRISHNA_SWE_REX_CMD",
        "arise": "KRISHNA_ARISE_CMD",
        "cua": "KRISHNA_CUA_CMD",
        "goose": "KRISHNA_GOOSE_CMD",
    }

    @staticmethod
    def _load_local_env() -> None:
        repo_root = Path(__file__).resolve().parents[2]
        candidates = [
            repo_root / "config" / "mythos-stack.env",
            Path(os.getenv("KRISHNA_CONFIG_ROOT", "")) / "mythos-stack.env"
            if os.getenv("KRISHNA_CONFIG_ROOT") else None,
        ]
        for path in candidates:
            if not path or not path.is_file():
                continue
            for raw in path.read_text(encoding="utf-8-sig").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if key and value and key not in os.environ:
                    os.environ[key] = value
            break

    @staticmethod
    def _resolve_command(cmd: str) -> str | None:
        if not cmd:
            return None
        expanded = os.path.expandvars(os.path.expanduser(cmd))
        p = Path(expanded)
        if p.is_file():
            return str(p)
        return shutil.which(expanded)

    def __init__(self):
        self._load_local_env()
        self._commands: Dict[str, str] = {}
        for name, (default, _, _) in self.DEFAULTS.items():
            self._commands[name] = os.getenv(self.ENV_OVERRIDES[name], default).strip()

    def command(self, name: str) -> str:
        if name not in self._commands:
            raise KeyError(name)
        return self._commands[name]

    def available(self, name: str) -> bool:
        return self._resolve_command(self.command(name)) is not None

    def statuses(self) -> List[dict]:
        out = []
        for name, (_, purpose, license_name) in self.DEFAULTS.items():
            cmd = self.command(name)
            out.append(asdict(ToolStatus(
                name=name,
                command=cmd,
                available=self._resolve_command(cmd) is not None,
                purpose=purpose,
                license=license_name,
            )))
        return out

    def run(self, name: str, args: List[str], cwd: str | None = None, timeout: int = 120) -> dict:
        """Run a known external adapter without shell expansion."""
        cmd = self.command(name)
        resolved = self._resolve_command(cmd)
        if not resolved:
            return {"ok": False, "available": False, "tool": name, "error": "tool not installed"}
        try:
            proc = subprocess.run(
                [resolved, *args],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=max(1, min(timeout, 1800)),
                shell=False,
            )
            return {
                "ok": proc.returncode == 0,
                "available": True,
                "tool": name,
                "returncode": proc.returncode,
                "stdout": proc.stdout[-20000:],
                "stderr": proc.stderr[-12000:],
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "available": True, "tool": name, "error": "timeout"}
        except OSError as exc:
            return {"ok": False, "available": True, "tool": name, "error": str(exc)}
