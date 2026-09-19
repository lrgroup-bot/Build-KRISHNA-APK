from __future__ import annotations
class AvatarRuntime:
 """Animation command bus for a rigged GLB once a rigged asset is installed."""
 ALLOWED={"idle","walk","smile","talk","listen","think","wave"}
 def command(self,action,**params):
  if action not in self.ALLOWED:raise ValueError("unsupported avatar action")
  return {"action":action,"params":params,"requires_rigged_glb":True}
 def lip_sync(self,phonemes):
  return {"action":"talk","phonemes":list(phonemes),"requires_morph_targets":True}
