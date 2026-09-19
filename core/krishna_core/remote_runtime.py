from __future__ import annotations
class RemoteRuntime:
 """Transport-neutral remote policy boundary. Public unauthenticated exposure is forbidden."""
 def __init__(self,pairing,capabilities):self.pairing=pairing;self.capabilities=capabilities
 def authorize(self,device_id,token,capability):
  if not self.pairing.verify(device_id,token):raise PermissionError("pairing required")
  self.capabilities.require(device_id,capability)
  return True
