import socket, time, threading
from typing import Callable, Optional

class Watcher:
    def __init__(self, targets=None, interval=60, on_transition: Optional[Callable[[dict], None]]=None):
        self.targets = targets or [("127.0.0.1", 11434)]
        self.interval = interval
        self.state = {}
        self.transitions = []
        self.running = False
        self.on_transition = on_transition
        self._lock = threading.RLock()

    def _check(self, host, port):
        started = time.perf_counter()
        try:
            with socket.create_connection((host, port), timeout=2):
                ok = True
        except OSError:
            ok = False
        latency_ms = int((time.perf_counter() - started) * 1000)
        return ok, latency_ms

    def snapshot(self):
        with self._lock:
            return {
                "targets": dict(self.state),
                "recent_transitions": list(self.transitions[:20]),
                "interval_seconds": self.interval,
            }

    def loop(self):
        self.running = True
        while self.running:
            for host, port in self.targets:
                key = f"{host}:{port}"
                ok, latency_ms = self._check(host, port)
                now = time.time()
                with self._lock:
                    old = self.state.get(key, {})
                    current = {
                        "ok": ok,
                        "latency_ms": latency_ms,
                        "checked_at": now,
                    }
                    self.state[key] = current
                    if old and old.get("ok") != ok:
                        transition = {
                            "target": key,
                            "from": old.get("ok"),
                            "to": ok,
                            "observed_at": now,
                        }
                        self.transitions.insert(0, transition)
                        del self.transitions[100:]
                        if self.on_transition:
                            try:
                                self.on_transition(transition)
                            except Exception:
                                pass
            time.sleep(self.interval)

    def start(self):
        if self.running:
            return
        threading.Thread(target=self.loop, daemon=True).start()

    def stop(self):
        self.running = False
