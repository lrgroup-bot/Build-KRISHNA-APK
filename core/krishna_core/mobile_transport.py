"""Authenticated mobile transport facade with durable idempotent command results."""
from __future__ import annotations
from .mobile_gateway import MobileGateway
from .realtime_session import RealtimeSessionStore

class MobileTransport:
    def __init__(self,gateway:MobileGateway,sessions:RealtimeSessionStore):
        self.gateway=gateway; self.sessions=sessions
    def connect(self,device_id,token,last_seq=0):
        if not self.gateway.pairing.verify(device_id,token):
            raise PermissionError("invalid device credential")
        return {"ok":True,"resume_after":int(last_seq),"events":self.sessions.after(device_id,last_seq)}
    def _completed(self,device_id,message_id):
        for event in reversed(self.sessions.after(device_id,0)):
            if event.get("type")=="command.completed" and event.get("payload",{}).get("message_id")==message_id:
                return event["payload"].get("result")
        return None
    def command(self,device_id,token,message_id,method,params):
        if not message_id: raise ValueError("message_id required")
        if not self.gateway.pairing.verify(device_id,token):
            raise PermissionError("invalid device credential")
        completed=self._completed(device_id,message_id)
        if completed is not None:return completed
        self.sessions.publish(device_id,"command.received",{"message_id":message_id,"method":method},idempotency_key="in:"+message_id)
        result=self.gateway.call(device_id,token,method,params)
        self.sessions.publish(device_id,"command.completed",{"message_id":message_id,"method":method,"result":result},idempotency_key="out:"+message_id)
        return result
    def notify(self,device_id,kind,payload):
        return self.sessions.publish(device_id,kind,payload)
