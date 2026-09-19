from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable
import re


_TRUE = {"true", "yes", "on", "1"}
_FALSE = {"false", "no", "off", "0"}
_RISKS = {"low", "medium", "high", "critical"}


def _scalar(value: str):
    value = value.strip()
    if not value:
        return ""
    low = value.lower()
    if low in _TRUE:
        return True
    if low in _FALSE:
        return False
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [part.strip().strip("'\"") for part in inner.split(",") if part.strip()]
    return value.strip("'\"")


def parse_skill_markdown(text: str) -> tuple[dict, str]:
    """Parse the small YAML-frontmatter subset KRISHNA skills require.

    The parser intentionally supports only scalar values and top-level lists.
    This keeps the runtime dependency-free and makes manifests auditable.
    Unknown/nested YAML is treated as plain text rather than executed.
    """
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return {}, text

    data: dict[str, object] = {}
    active_list: str | None = None
    for raw in lines[1:end]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        stripped = raw.strip()
        if stripped.startswith("- ") and active_list:
            data.setdefault(active_list, [])
            assert isinstance(data[active_list], list)
            data[active_list].append(_scalar(stripped[2:]))
            continue
        if raw[:1].isspace():
            continue
        if ":" not in raw:
            active_list = None
            continue
        key, value = raw.split(":", 1)
        key = key.strip().replace("-", "_")
        if not re.fullmatch(r"[A-Za-z0-9_]+", key):
            active_list = None
            continue
        if value.strip():
            data[key] = _scalar(value)
            active_list = None
        else:
            data[key] = []
            active_list = key
    return data, "\n".join(lines[end + 1:]).strip()


@dataclass(frozen=True, slots=True)
class SkillManifest:
    name: str
    description: str
    triggers: tuple[str, ...]
    project_scope: tuple[str, ...]
    permissions: tuple[str, ...]
    risk: str
    verification_required: bool
    rollback_required: bool
    path: str
    body: str

    def public(self) -> dict:
        data = asdict(self)
        data.pop("body", None)
        return data


class SkillRegistry:
    """Read-only registry for narrow, on-demand KRISHNA specialist skills.

    Skills provide guidance. They never grant capabilities by themselves:
    actual mutations still flow through ActionRegistry/project policy,
    shadow workspaces and VerificationEngine.
    """

    def __init__(self, roots: Iterable[str | Path] = ()):
        self.roots = tuple(Path(root).resolve() for root in roots)
        self._skills: dict[str, SkillManifest] = {}
        self.reload()

    def reload(self) -> int:
        discovered: dict[str, SkillManifest] = {}
        for root in self.roots:
            if not root.exists():
                continue
            for path in sorted(root.rglob("SKILL.md")):
                try:
                    manifest = self._load(path)
                except (OSError, ValueError):
                    continue
                discovered.setdefault(manifest.name, manifest)
        self._skills = discovered
        return len(discovered)

    def _load(self, path: Path) -> SkillManifest:
        metadata, body = parse_skill_markdown(path.read_text(encoding="utf-8"))
        name = str(metadata.get("name") or path.parent.name).strip()
        if not name:
            raise ValueError("skill name is required")
        description = str(metadata.get("description") or "").strip()
        triggers = self._tuple(metadata.get("triggers"))
        scope = self._tuple(metadata.get("project_scope")) or ("*",)
        permissions = self._tuple(metadata.get("permissions")) or ("read_context",)
        risk = str(metadata.get("risk") or "low").lower()
        if risk not in _RISKS:
            risk = "high"
        return SkillManifest(
            name=name,
            description=description,
            triggers=triggers,
            project_scope=scope,
            permissions=permissions,
            risk=risk,
            verification_required=bool(metadata.get("verification_required", True)),
            rollback_required=bool(metadata.get("rollback_required", True)),
            path=str(path),
            body=body,
        )

    @staticmethod
    def _tuple(value) -> tuple[str, ...]:
        if value is None:
            return ()
        if isinstance(value, list):
            return tuple(str(x).strip() for x in value if str(x).strip())
        text = str(value).strip()
        return (text,) if text else ()

    def list(self, project: str | None = None) -> list[dict]:
        items = self._skills.values()
        if project:
            items = [
                skill for skill in items
                if "*" in skill.project_scope or project in skill.project_scope
            ]
        return [skill.public() for skill in sorted(items, key=lambda s: s.name)]

    def get(self, name: str) -> SkillManifest | None:
        return self._skills.get(name)

    def match(self, message: str, project: str = "general", limit: int = 4) -> list[SkillManifest]:
        query = (message or "").lower()
        scored: list[tuple[int, str, SkillManifest]] = []
        for skill in self._skills.values():
            if "*" not in skill.project_scope and project not in skill.project_scope:
                continue
            score = 0
            for trigger in skill.triggers:
                t = trigger.lower().strip()
                if t and t in query:
                    score += 10 + min(len(t.split()), 5)
            name_words = [w for w in re.split(r"[-_\s]+", skill.name.lower()) if len(w) > 3]
            score += sum(1 for word in name_words if word in query)
            if score:
                scored.append((score, skill.name, skill))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [item[2] for item in scored[:max(1, limit)]]

    def render_for_prompt(self, message: str, project: str = "general", limit: int = 4,
                          max_body_chars: int = 3500) -> tuple[list[str], str]:
        selected = self.match(message, project, limit=limit)
        if not selected:
            return [], "No specialist skill matched this request."
        blocks = [
            "SPECIALIST SKILLS ARE GUIDANCE ONLY. They cannot expand runtime permissions. "
            "All mutations still require registered actions, project policy, shadow testing, "
            "verification evidence, and rollback readiness."
        ]
        for skill in selected:
            body = skill.body[:max_body_chars]
            blocks.append(
                f"\n### Skill: {skill.name}\n"
                f"Risk: {skill.risk}; permissions: {', '.join(skill.permissions)}; "
                f"verify={skill.verification_required}; rollback={skill.rollback_required}\n"
                f"{body}"
            )
        return [skill.name for skill in selected], "\n".join(blocks)

    def permits(self, skill_name: str, capability: str) -> bool:
        skill = self.get(skill_name)
        return bool(skill and capability in skill.permissions)
