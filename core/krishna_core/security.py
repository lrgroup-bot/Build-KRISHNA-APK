from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable


SECRET_PATTERNS = [
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("generic_token", re.compile(r"(?i)\b(?:api[_-]?key|secret|token|password)\b\s*[:=]\s*['\"][^'\"]{8,}['\"]")),
]

RISKY_CODE_PATTERNS = [
    ("python_eval", re.compile(r"\beval\s*\(")),
    ("python_exec", re.compile(r"\bexec\s*\(")),
    ("shell_true", re.compile(r"shell\s*=\s*True")),
    ("os_system", re.compile(r"\bos\.system\s*\(")),
]


class DefensiveSecurityScanner:
    """Defensive static checks for KRISHNA-owned/authorized project text files."""

    def scan_text(self, path: str, text: str) -> list[dict]:
        findings = []
        for name, pattern in SECRET_PATTERNS:
            for match in pattern.finditer(text):
                findings.append({
                    "severity": "high",
                    "category": "secret_exposure",
                    "rule": name,
                    "path": path,
                    "line": text.count("\n", 0, match.start()) + 1,
                })
        for name, pattern in RISKY_CODE_PATTERNS:
            for match in pattern.finditer(text):
                findings.append({
                    "severity": "medium",
                    "category": "dangerous_execution_pattern",
                    "rule": name,
                    "path": path,
                    "line": text.count("\n", 0, match.start()) + 1,
                })
        return findings

    def scan_paths(self, paths: Iterable[str]) -> dict:
        findings = []
        scanned = 0
        for raw in paths:
            path = Path(raw)
            if not path.is_file():
                continue
            if path.stat().st_size > 2_000_000:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            scanned += 1
            findings.extend(self.scan_text(str(path), text))
        return {"scanned_files": scanned, "findings": findings}
