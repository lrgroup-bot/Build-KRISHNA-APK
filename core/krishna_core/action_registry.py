from __future__ import annotations

from dataclasses import dataclass, asdict
from threading import RLock
from typing import Callable, Dict


@dataclass
class RegisteredAction:
    name: str
    project: str
    mutating: bool
    description: str


class ActionRegistry:
    """Pre-registered actions only; natural language never becomes a shell command."""

    def __init__(self):
        self._lock = RLock()
        self._actions: Dict[tuple[str, str], tuple[RegisteredAction, Callable[[dict], dict]]] = {}

    def register(self, project: str, name: str, fn: Callable[[dict], dict],
                 mutating: bool = False, description: str = "") -> dict:
        item = RegisteredAction(name=name, project=project, mutating=mutating, description=description)
        with self._lock:
            self._actions[(project, name)] = (item, fn)
        return asdict(item)

    def list(self, project: str | None = None) -> list[dict]:
        with self._lock:
            items = [v[0] for v in self._actions.values() if project is None or v[0].project == project]
        return [asdict(x) for x in sorted(items, key=lambda x: (x.project, x.name))]

    def execute(self, project: str, name: str, payload: dict | None = None,
                allow_mutation: bool = False) -> dict:
        with self._lock:
            pair = self._actions.get((project, name))
        if not pair:
            raise KeyError(f"{project}:{name}")
        meta, fn = pair
        if meta.mutating and not allow_mutation:
            return {"executed": False, "blocked": True, "reason": "mutating action disabled", "action": asdict(meta)}
        result = fn(payload or {})
        return {"executed": True, "blocked": False, "action": asdict(meta), "result": result}
