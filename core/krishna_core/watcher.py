import socket, time, threading

class Watcher:
    def __init__(self, targets=None, interval=60):
        self.targets=targets or [("127.0.0.1",11434)]
        self.interval=interval; self.state={}; self.running=False
    def _check(self, host, port):
        try:
            with socket.create_connection((host,port),timeout=2): return True
        except OSError: return False
    def loop(self):
        self.running=True
        while self.running:
            for h,p in self.targets: self.state[f"{h}:{p}"]=self._check(h,p)
            time.sleep(self.interval)
    def start(self): threading.Thread(target=self.loop,daemon=True).start()
    def stop(self): self.running=False
