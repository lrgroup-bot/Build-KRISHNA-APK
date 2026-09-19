from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List, Set, Tuple
import threading


@dataclass(frozen=True)
class ProjectNode:
    name: str
    kind: str
    metadata: dict


class ProjectGraph:
    """Thread-safe lightweight dependency/relationship graph for KRISHNA projects."""

    def __init__(self):
        self._nodes: Dict[str, ProjectNode] = {}
        self._edges: Dict[str, Set[Tuple[str, str]]] = {}
        self._lock = threading.RLock()

    def upsert_node(self, name: str, kind: str = "component", metadata: dict | None = None) -> None:
        with self._lock:
            self._nodes[name] = ProjectNode(name=name, kind=kind, metadata=metadata or {})

    def link(self, source: str, target: str, relation: str = "depends_on") -> None:
        with self._lock:
            self._edges.setdefault(source, set()).add((relation, target))

    def neighbors(self, name: str) -> List[dict]:
        with self._lock:
            return [
                {"relation": rel, "target": target}
                for rel, target in sorted(self._edges.get(name, set()))
            ]

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "nodes": [asdict(v) for _, v in sorted(self._nodes.items())],
                "edges": [
                    {"source": src, "relation": rel, "target": target}
                    for src, pairs in sorted(self._edges.items())
                    for rel, target in sorted(pairs)
                ],
            }

    def relevant(self, seeds: List[str], depth: int = 2) -> dict:
        with self._lock:
            seen = set(seeds)
            frontier = list(seeds)
            for _ in range(max(depth, 0)):
                nxt = []
                for node in frontier:
                    for _, target in self._edges.get(node, set()):
                        if target not in seen:
                            seen.add(target)
                            nxt.append(target)
                    for src, pairs in self._edges.items():
                        if any(target == node for _, target in pairs) and src not in seen:
                            seen.add(src)
                            nxt.append(src)
                frontier = nxt
            return {
                "nodes": [asdict(self._nodes[n]) for n in sorted(seen) if n in self._nodes],
                "edges": [
                    {"source": src, "relation": rel, "target": target}
                    for src, pairs in self._edges.items()
                    for rel, target in pairs
                    if src in seen and target in seen
                ],
            }
