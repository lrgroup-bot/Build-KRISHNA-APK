"""Authenticated mobile transport facade with resumable event delivery."""
from __future__ import annotations
from .mobile_gateway import MobileGateway
from .realtime_session import RealtimeSessionStore

class MobileTransport:
    def __init__(self,gateway:MobileGateway,sessions:RealtimeSessionStore): self.gateway=gateway; self.sessions=sessions
    def connect(self,device_id,token,last_seq=0):
        if not self.gateway.pairing.verify(device_id,token): raise PermissionError("invalid device credential")
        return {"ok":True,"resume_after":int(last_seq),"events":self.sessions.after(device_id,last_seq)}
    def command(self,device_id,token,message_id,method,params):
        if not message_id: raise ValueError("message_id required")
        prior=self.sessions.publish(device_id,"command.received",{"method":method},idempotency_key="in:"+message_id)
        if prior["payload"].get("completed"): return prior["payload"]["result"]
        result=self.gateway.call(device_id,token,method,params)
        self.sessions.publish(device_id,"command.completed",{"message_id":message_id,"method":method,"result":result})
        return result
    def notify(self,device_id,kind,payload): return self.sessions.publish(device_id,kind,payload)
