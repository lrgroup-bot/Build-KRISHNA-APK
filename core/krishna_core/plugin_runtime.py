from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from threading import RLock
import time
import uuid


_SLUG = re.compile(r"^[a-z][a-z0-9_-]{1,63}$")
_KINDS = {"builtin", "local", "http", "mcp", "connector", "custom"}
_AUTH = {"none", "token", "api_key", "oauth", "device", "local"}
_RISKS = {"low", "medium", "high", "critical"}


@dataclass(slots=True)
class PluginManifest:
    id: str
    name: str
    description: str = ""
    kind: str = "custom"
    endpoint: str = ""
    auth_type: str = "none"
    permissions: tuple[str, ...] = ()
    project_scope: tuple[str, ...] = ("*",)
    risk: str = "medium"
    enabled: bool = False
    builtin: bool = False
    created_at: float = 0.0
    updated_at: float = 0.0

    def public(self) -> dict:
        data = asdict(self)
        data["permissions"] = list(self.permissions)
        data["project_scope"] = list(self.project_scope)
        return data


class PluginRegistry:
    """Persistent, provider-neutral plugin catalog.

    A manifest declares what a plugin *wants*. It does not grant execution
    authority, expose credentials, or bypass project/action policy.
    """

    def __init__(self, state_dir: str | Path):
        self.root = Path(state_dir).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "plugins.json"
        self.lock = RLock()
        self._items: dict[str, PluginManifest] = {}
        self._load()
        self._seed()

    def _load(self):
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        for row in raw if isinstance(raw, list) else []:
            try:
                item = self._coerce(row, preserve_times=True)
                self._items[item.id] = item
            except ValueError:
                continue

    def _save(self):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps([x.public() for x in self._items.values()], indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def _seed(self):
        defaults = [
            {"id":"pc","name":"PC","description":"Local registered projects, browser inspection, logs and approved PC actions.","kind":"local","auth_type":"local","permissions":["projects.read","files.read","browser.inspect","logs.read"],"risk":"high","builtin":True},
            {"id":"github","name":"GitHub","description":"Repositories, issues, pull requests and CI workflows through an authorized connector.","kind":"connector","auth_type":"oauth","permissions":["repos.read","issues.read","pull_requests.read","actions.read"],"risk":"medium","builtin":True},
        ]
        changed = False
        for row in defaults:
            if row["id"] not in self._items:
                row["enabled"] = False
                self._items[row["id"]] = self._coerce(row)
                changed = True
        if changed:
            self._save()

    def _coerce(self, data: dict, preserve_times: bool = False) -> PluginManifest:
        pid = str(data.get("id") or "").strip().lower()
        if not pid:
            pid = re.sub(r"[^a-z0-9_-]+", "-", str(data.get("name") or "").strip().lower()).strip("-")
        if not _SLUG.fullmatch(pid):
            raise ValueError("plugin id must use lowercase letters, numbers, _ or -")
        name = str(data.get("name") or pid).strip()[:100]
        if not name:
            raise ValueError("plugin name is required")
        kind = str(data.get("kind") or "custom").strip().lower()
        if kind not in _KINDS:
            raise ValueError("unsupported plugin kind")
        auth = str(data.get("auth_type") or "none").strip().lower()
        if auth not in _AUTH:
            raise ValueError("unsupported auth type")
        risk = str(data.get("risk") or "medium").strip().lower()
        if risk not in _RISKS:
            raise ValueError("unsupported risk")
        perms = tuple(sorted({str(x).strip() for x in data.get("permissions") or [] if str(x).strip()}))
        scope = tuple(sorted({str(x).strip() for x in data.get("project_scope") or ["*"] if str(x).strip()})) or ("*",)
        now = time.time()
        created = float(data.get("created_at") or now) if preserve_times else now
        updated = float(data.get("updated_at") or now) if preserve_times else now
        return PluginManifest(
            id=pid, name=name, description=str(data.get("description") or "")[:800],
            kind=kind, endpoint=str(data.get("endpoint") or "")[:1000],
            auth_type=auth, permissions=perms, project_scope=scope, risk=risk,
            enabled=bool(data.get("enabled", False)), builtin=bool(data.get("builtin", False)),
            created_at=created, updated_at=updated,
        )

    def list(self) -> list[dict]:
        with self.lock:
            return [x.public() for x in sorted(self._items.values(), key=lambda p: (not p.builtin, p.name.lower()))]

    def add(self, data: dict) -> dict:
        item = self._coerce(data)
        with self.lock:
            if item.id in self._items:
                raise ValueError("plugin already exists")
            self._items[item.id] = item
            self._save()
        return item.public()

    def set_enabled(self, plugin_id: str, enabled: bool) -> dict:
        with self.lock:
            item = self._items.get(plugin_id)
            if not item:
                raise KeyError(plugin_id)
            item.enabled = bool(enabled)
            item.updated_at = time.time()
            self._save()
            return item.public()

    def remove(self, plugin_id: str) -> bool:
        with self.lock:
            item = self._items.get(plugin_id)
            if not item:
                return False
            if item.builtin:
                raise PermissionError("builtin plugins cannot be removed")
            del self._items[plugin_id]
            self._save()
            return True
