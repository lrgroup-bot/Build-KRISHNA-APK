from __future__ import annotations
import threading,time

class AutonomyLoop:
    """Bounded supervisor. It observes registered projects and records incidents;
    mutation remains behind each project's allowlist + shadow verification gate."""
    def __init__(self,orchestrator,ledger,interval=60):
        self.o=orchestrator;self.ledger=ledger;self.interval=max(15,int(interval));self.stop_event=threading.Event();self.thread=None
    def start(self):
        if self.thread and self.thread.is_alive():return
        self.stop_event.clear();self.thread=threading.Thread(target=self._run,name="krishna-autonomy",daemon=True);self.thread.start()
    def stop(self):self.stop_event.set()
    def _run(self):
        while not self.stop_event.is_set():
            for p in self.o.projects.list():
                try:
                    root=p.get("root")
                    if root:self.o.index_project(p["name"])
                except Exception as exc:
                    self.o.memory.audit("autonomy_observe","failed",f'{p.get("name")}:{type(exc).__name__}:{exc}')
            self.stop_event.wait(self.interval)
