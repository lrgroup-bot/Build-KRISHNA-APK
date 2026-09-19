from __future__ import annotations

from dataclasses import dataclass, asdict
from collections import deque
from threading import RLock
import time
import uuid


@dataclass(frozen=True)
class NeuralEvent:
    id: str
    source: str
    kind: str
    severity: str
    detail: str
    project: str
    payload: dict
    observed_at: float


class NeuralActionGraph:
    """Fast event/reflex layer beneath KRISHNA's slower reasoning loop.

    It never executes arbitrary commands. It classifies events, emits bounded
    intents, records state, and leaves mutating work to registered/policy-gated
    KRISHNA actions.
    """

    SEVERITY_ORDER = {"info": 0, "notice": 1, "warning": 2, "critical": 3}

    def __init__(self, history_limit: int = 200):
        self._lock = RLock()
        self._history = deque(maxlen=max(20, history_limit))
        self._counts = {}
        self._last_intent = None

    def ingest(self, source: str, kind: str, detail: str = "", *,
               severity: str = "info", project: str = "system",
               payload: dict | None = None) -> dict:
        severity = severity if severity in self.SEVERITY_ORDER else "info"
        event = NeuralEvent(
            id=str(uuid.uuid4()),
            source=(source or "unknown")[:64],
            kind=(kind or "event")[:96],
            severity=severity,
            detail=(detail or "")[:2000],
            project=(project or "system")[:128],
            payload=dict(payload or {}),
            observed_at=time.time(),
        )
        intent = self._route(event)
        record = {"event": asdict(event), "intent": intent}
        with self._lock:
            self._history.appendleft(record)
            self._counts[event.kind] = self._counts.get(event.kind, 0) + 1
            self._last_intent = intent
        return record

    def _route(self, event: NeuralEvent) -> dict:
        kind = event.kind.lower()
        detail = event.detail.lower()

        if kind in {"service_down", "watcher_down", "endpoint_down"}:
            return self._intent("investigate_recovery", "high", True,
                                "Collect evidence, diagnose the service, then use the registered recovery ladder.")
        if kind in {"test_failed", "build_failed", "project_error", "exception"}:
            return self._intent("investigate_project", "high", True,
                                "Collect project evidence and create a shadow repair candidate before any live mutation.")
        if kind in {"cpu_pressure", "memory_pressure", "thermal_pressure"}:
            return self._intent("throttle_work", "critical" if event.severity == "critical" else "high", False,
                                "Reduce autonomous concurrency and defer non-essential work.")
        if kind in {"repo_changed", "file_changed"}:
            return self._intent("refresh_project_context", "normal", False,
                                "Refresh repository/project graph context before further work.")
        if kind in {"user_command", "mobile_command", "voice_command"}:
            return self._intent("reason_about_command", "high", True,
                                "Route the user's request through KRISHNA reasoning and registered capabilities.")
        if kind in {"mobile_foreground", "mobile_connected", "pc_connected"}:
            return self._intent("sync_context", "normal", False,
                                "Synchronize current KRISHNA state and recent verified work.")
        if kind in {"mobile_background", "mobile_disconnected"}:
            return self._intent("preserve_state", "low", False,
                                "Persist context; continue only policy-approved autonomous PC work.")
        if kind in {"task_completed", "repair_verified", "service_recovered"}:
            return self._intent("notify_verified_completion", "normal", False,
                                "Surface a concise completion update only when verification evidence exists.")
        if "credential" in detail or "secret" in detail:
            return self._intent("security_review", "critical", True,
                                "Run defensive security checks and avoid exposing sensitive data.")
        return self._intent("observe", "low", False,
                            "Record the event and wait for corroborating context unless escalation is warranted.")

    @staticmethod
    def _intent(name: str, priority: str, requires_reasoning: bool, guidance: str) -> dict:
        return {
            "name": name,
            "priority": priority,
            "requires_reasoning": requires_reasoning,
            "guidance": guidance,
            "mutating": False,
        }

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "architecture": "KRISHNA Neural Action Graph",
                "mode": "observe-route-escalate",
                "events_seen": sum(self._counts.values()),
                "counts": dict(self._counts),
                "last_intent": dict(self._last_intent) if self._last_intent else None,
                "recent": list(self._history)[:30],
            }
