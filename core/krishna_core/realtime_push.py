from __future__ import annotations
import threading,time
class RealtimePush:
 """Dependency-free long-poll push facade over durable sessions."""
 def __init__(self,sessions):self.sessions=sessions
 def wait(self,device_id,after=0,timeout=25.0,interval=.25):
  deadline=time.monotonic()+min(max(float(timeout),0),30)
  while time.monotonic()<deadline:
   events=self.sessions.after(device_id,after)
   if events:return events
   time.sleep(interval)
  return []
