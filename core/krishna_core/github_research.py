from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime, timezone


@dataclass
class RepoCandidate:
    full_name: str
    html_url: str
    description: str
    stars: int
    language: str | None
    license: str | None
    archived: bool
    pushed_at: str | None
    score: float
    reasons: list[str]


class GitHubResearchAgent:
    """Public GitHub research with explicit license/activity/security metadata."""

    SAFE_LICENSES = {
        "MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC",
        "MPL-2.0", "LGPL-2.1", "LGPL-3.0",
    }

    def __init__(self, token: str | None = None):
        self.token = token or os.getenv("GITHUB_TOKEN", "")

    def _get(self, url: str) -> dict:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "KRISHNA-Research-Agent",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def evaluate(repo: dict) -> RepoCandidate:
        stars = int(repo.get("stargazers_count") or 0)
        license_name = ((repo.get("license") or {}).get("spdx_id") or None)
        archived = bool(repo.get("archived"))
        pushed_at = repo.get("pushed_at")
        score = 0.0
        reasons: list[str] = []

        if not archived:
            score += 2.0
            reasons.append("active repository")
        else:
            score -= 5.0
            reasons.append("archived")

        if license_name in GitHubResearchAgent.SAFE_LICENSES:
            score += 3.0
            reasons.append(f"compatible license metadata: {license_name}")
        elif license_name:
            reasons.append(f"license requires review: {license_name}")
        else:
            score -= 2.0
            reasons.append("no SPDX license metadata")

        if stars >= 10000:
            score += 3.0
            reasons.append("high adoption")
        elif stars >= 1000:
            score += 2.0
            reasons.append("established adoption")
        elif stars >= 100:
            score += 1.0

        if pushed_at:
            try:
                pushed = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
                age_days = (datetime.now(timezone.utc) - pushed).days
                if age_days <= 90:
                    score += 2.0
                    reasons.append("recently maintained")
                elif age_days > 730:
                    score -= 1.5
                    reasons.append("maintenance appears stale")
            except ValueError:
                pass

        return RepoCandidate(
            full_name=str(repo.get("full_name", "")),
            html_url=str(repo.get("html_url", "")),
            description=str(repo.get("description") or ""),
            stars=stars,
            language=repo.get("language"),
            license=license_name,
            archived=archived,
            pushed_at=pushed_at,
            score=round(score, 2),
            reasons=reasons,
        )

    def search(self, query: str, limit: int = 10) -> dict:
        if not query.strip():
            raise ValueError("research query is required")
        limit = max(1, min(25, int(limit)))
        encoded = urllib.parse.quote(query)
        data = self._get(
            f"https://api.github.com/search/repositories?q={encoded}&sort=stars&order=desc&per_page={limit}"
        )
        candidates = [self.evaluate(item) for item in data.get("items", [])]
        candidates.sort(key=lambda x: x.score, reverse=True)
        return {
            "query": query,
            "count": len(candidates),
            "candidates": [asdict(x) for x in candidates],
            "policy": {
                "auto_live_integration": False,
                "required_before_integration": [
                    "license review",
                    "defensive security scan",
                    "dependency review",
                    "shadow integration",
                    "project tests",
                    "browser/backend verification",
                ],
            },
        }
