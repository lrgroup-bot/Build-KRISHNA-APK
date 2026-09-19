from __future__ import annotations

import ctypes
import os
import threading
import time
from pathlib import Path
from typing import Callable, Optional


class PCObserver:
    """Low-overhead PC sensor for KRISHNA's event layer.

    Emits transitions, not a continuous stream, so the reasoning layer is not
    flooded. No mutation is performed here.
    """

    SKIP_DIRS = {
        ".git", ".idea", ".gradle", ".venv", "venv", "__pycache__",
        "node_modules", "build", "dist", ".next", ".expo",
    }

    def __init__(
        self,
        project_supplier: Callable[[], list[dict]],
        on_event: Optional[Callable[[dict], None]] = None,
        *,
        cpu_budget_percent: int = 60,
        memory_budget_percent: int = 70,
        interval: float = 15.0,
        max_files_per_project: int = 5000,
    ):
        self.project_supplier = project_supplier
        self.on_event = on_event
        self.cpu_budget = int(cpu_budget_percent)
        self.memory_budget = int(memory_budget_percent)
        self.interval = max(5.0, float(interval))
        self.max_files_per_project = max(100, int(max_files_per_project))
        self.running = False
        self._thread = None
        self._lock = threading.RLock()
        self._pressure = {"cpu": False, "memory": False}
        self._project_signatures: dict[str, tuple[int, int]] = {}
        self._last_cpu_times = None
        self._snapshot = {
            "cpu_percent": None,
            "memory_percent": None,
            "pressure": dict(self._pressure),
            "projects_watched": 0,
            "checked_at": None,
        }

    @staticmethod
    def _filetime_value(value) -> int:
        return (int(value.dwHighDateTime) << 32) | int(value.dwLowDateTime)

    def _windows_cpu_percent(self):
        class FILETIME(ctypes.Structure):
            _fields_ = [("dwLowDateTime", ctypes.c_ulong), ("dwHighDateTime", ctypes.c_ulong)]

        idle, kernel, user = FILETIME(), FILETIME(), FILETIME()
        if not ctypes.windll.kernel32.GetSystemTimes(
            ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)
        ):
            return None
        now = (
            self._filetime_value(idle),
            self._filetime_value(kernel),
            self._filetime_value(user),
        )
        previous = self._last_cpu_times
        self._last_cpu_times = now
        if previous is None:
            return None
        idle_delta = now[0] - previous[0]
        total_delta = (now[1] - previous[1]) + (now[2] - previous[2])
        if total_delta <= 0:
            return None
        return max(0.0, min(100.0, 100.0 * (1.0 - idle_delta / total_delta)))

    def _linux_cpu_percent(self):
        try:
            fields = Path("/proc/stat").read_text(encoding="utf-8").splitlines()[0].split()[1:]
            values = [int(x) for x in fields]
        except (OSError, ValueError, IndexError):
            return None
        idle = values[3] + (values[4] if len(values) > 4 else 0)
        total = sum(values)
        now = (idle, total)
        previous = self._last_cpu_times
        self._last_cpu_times = now
        if previous is None:
            return None
        idle_delta = now[0] - previous[0]
        total_delta = now[1] - previous[1]
        if total_delta <= 0:
            return None
        return max(0.0, min(100.0, 100.0 * (1.0 - idle_delta / total_delta)))

    def _cpu_percent(self):
        if os.name == "nt":
            try:
                return self._windows_cpu_percent()
            except Exception:
                return None
        if Path("/proc/stat").exists():
            return self._linux_cpu_percent()
        try:
            load = os.getloadavg()[0]
            cpus = max(1, os.cpu_count() or 1)
            return max(0.0, min(100.0, load / cpus * 100.0))
        except (AttributeError, OSError):
            return None

    @staticmethod
    def _windows_memory_percent():
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        state = MEMORYSTATUSEX()
        state.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state)):
            return None
        return float(state.dwMemoryLoad)

    @staticmethod
    def _linux_memory_percent():
        try:
            values = {}
            for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
                key, raw = line.split(":", 1)
                values[key] = int(raw.strip().split()[0])
            total = values["MemTotal"]
            available = values.get("MemAvailable", values.get("MemFree", 0))
            if total <= 0:
                return None
            return max(0.0, min(100.0, (total - available) / total * 100.0))
        except (OSError, ValueError, KeyError):
            return None

    def _memory_percent(self):
        if os.name == "nt":
            try:
                return self._windows_memory_percent()
            except Exception:
                return None
        if Path("/proc/meminfo").exists():
            return self._linux_memory_percent()
        return None

    def _project_signature(self, root: str) -> tuple[int, int]:
        base = Path(root)
        if not base.exists():
            return (0, 0)
        latest_ns = 0
        count = 0
        try:
            for current, dirs, files in os.walk(base):
                dirs[:] = [d for d in dirs if d not in self.SKIP_DIRS]
                for name in files:
                    if count >= self.max_files_per_project:
                        return (count, latest_ns)
                    path = Path(current) / name
                    try:
                        latest_ns = max(latest_ns, path.stat().st_mtime_ns)
                        count += 1
                    except OSError:
                        continue
        except OSError:
            pass
        return (count, latest_ns)

    def _emit(self, kind: str, detail: str, *, severity="info", project="system", payload=None):
        if not self.on_event:
            return
        try:
            self.on_event({
                "source": "pc_observer",
                "kind": kind,
                "detail": detail,
                "severity": severity,
                "project": project,
                "payload": payload or {},
            })
        except Exception:
            pass

    def sample_once(self):
        cpu = self._cpu_percent()
        memory = self._memory_percent()

        for key, value, budget, kind in (
            ("cpu", cpu, self.cpu_budget, "cpu_pressure"),
            ("memory", memory, self.memory_budget, "memory_pressure"),
        ):
            if value is None:
                continue
            over = value >= budget
            was_over = self._pressure[key]
            if over and not was_over:
                self._emit(
                    kind,
                    f"{key.upper()} usage {value:.1f}% reached KRISHNA budget {budget}%",
                    severity="critical" if value >= 90 else "warning",
                    payload={"percent": round(value, 1), "budget_percent": budget},
                )
            elif not over and was_over:
                self._emit(
                    "resource_recovered",
                    f"{key.upper()} usage returned below KRISHNA budget ({value:.1f}% < {budget}%)",
                    severity="notice",
                    payload={"resource": key, "percent": round(value, 1), "budget_percent": budget},
                )
            self._pressure[key] = over

        projects = self.project_supplier() or []
        for item in projects:
            name = str(item.get("name", "")).strip()
            root = str(item.get("root", "")).strip()
            if not name or not root:
                continue
            signature = self._project_signature(root)
            previous = self._project_signatures.get(name)
            self._project_signatures[name] = signature
            if previous is not None and signature != previous:
                self._emit(
                    "repo_changed",
                    f"Registered project changed: {name}",
                    severity="notice",
                    project=name,
                    payload={"previous": previous, "current": signature},
                )

        with self._lock:
            self._snapshot = {
                "cpu_percent": None if cpu is None else round(cpu, 1),
                "memory_percent": None if memory is None else round(memory, 1),
                "pressure": dict(self._pressure),
                "projects_watched": len(projects),
                "checked_at": time.time(),
            }
        return self.snapshot()

    def snapshot(self):
        with self._lock:
            return dict(self._snapshot)

    def _loop(self):
        self.running = True
        while self.running:
            self.sample_once()
            time.sleep(self.interval)

    def start(self):
        if self.running:
            return
        self._thread = threading.Thread(target=self._loop, daemon=True, name="krishna-pc-observer")
        self._thread.start()

    def stop(self):
        self.running = False
