from dataclasses import dataclass
from typing import Callable, Dict

@dataclass
class Worker:
    name: str
    run: Callable[[dict], dict]

class WorkerRegistry:
    def __init__(self): self._workers: Dict[str, Worker] = {}
    def register(self, worker: Worker): self._workers[worker.name]=worker
    def names(self): return sorted(self._workers)
    def execute(self, name, payload):
        if name not in self._workers: raise KeyError(name)
        return self._workers[name].run(payload)
