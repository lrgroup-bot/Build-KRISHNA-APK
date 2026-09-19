from __future__ import annotations

from pathlib import Path
import json
import os
import time
import urllib.request

from .investigator import Evidence


class LocalEvidenceCollectors:
    """Safe, bounded evidence collectors for registered local projects."""

    def project_files(self, context: dict):
        root = context.get("project_root")
        if not root:
            return []
        p = Path(root)
        if not p.exists():
            return [Evidence("project_files", "missing_root", str(p), 1.0)]
        names = []
        for child in sorted(p.iterdir())[:80]:
            names.append(child.name + ("/" if child.is_dir() else ""))
        return [Evidence("project_files", "root_listing", "\n".join(names), 0.8)]

    def recent_logs(self, context: dict):
        root = context.get("project_root")
        if not root:
            return []
        now = time.time()
        rows = []
        for path in Path(root).rglob("*.log"):
            try:
                st = path.stat()
                if now - st.st_mtime > 7 * 86400 or st.st_size > 2_000_000:
                    continue
                tail = path.read_text(encoding="utf-8", errors="replace")[-5000:]
                rows.append(f"[{path.name}]\n{tail}")
                if len(rows) >= 5:
                    break
            except OSError:
                continue
        return [Evidence("recent_logs", "log_tail", "\n\n".join(rows), 0.9)] if rows else []

    def manifests(self, context: dict):
        root = context.get("project_root")
        if not root:
            return []
        p = Path(root)
        candidates = ["pyproject.toml", "requirements.txt", "package.json", "package-lock.json", "gradle.properties", "build.gradle", "settings.gradle"]
        found = []
        for name in candidates:
            path = p / name
            if path.exists() and path.is_file():
                try:
                    found.append(f"## {name}\n{path.read_text(encoding='utf-8', errors='replace')[:6000]}")
                except OSError:
                    pass
        return [Evidence("manifests", "dependency_manifest", "\n\n".join(found), 0.9)] if found else []

    @staticmethod
    def endpoint_probe(url: str, timeout: float = 3.0):
        def collect(context: dict):
            started = time.perf_counter()
            try:
                with urllib.request.urlopen(url, timeout=timeout) as resp:
                    body = resp.read(1000).decode("utf-8", errors="replace")
                    detail = json.dumps({"url": url, "status": resp.status, "latency_ms": int((time.perf_counter()-started)*1000), "body": body})
                    return [Evidence("endpoint", "http_response", detail, 1.0)]
            except Exception as exc:
                return [Evidence("endpoint", "http_error", f"{url}: {type(exc).__name__}: {exc}", 1.0)]
        return collect
