"""Transport-neutral secure mobile gateway primitives.

Network/WebSocket adapters authenticate here, then pass only allowlisted RPC calls
to MobileRPC. Raw shell, filesystem and credential APIs are intentionally absent.
"""
from __future__ import annotations
from dataclasses import dataclass
from .device_pairing import DevicePairingStore
from .mobile_rpc import MobileRPC

@dataclass
class MobileGateway:
    pairing:DevicePairingStore
    rpc:MobileRPC
    def pairing_request(self,device_id:str,name:str): return self.pairing.request(device_id,name)
    def pairing_approve(self,request_id:str): return self.pairing.approve(request_id)
    def call(self,device_id:str,token:str,method:str,params:dict):
        if not self.pairing.verify(device_id,token): raise PermissionError("unpaired or invalid device")
        return self.rpc.dispatch(method,params)
