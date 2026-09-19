from __future__ import annotations
class RuntimeReadiness:
 def report(self,*,gnn=None,voice=None,avatar=None,remote=None):
  return {"gnn":gnn or {},"voice":voice or {},"avatar":avatar or {},"remote":remote or {},"production_ready":all(bool(x and x.get("ready")) for x in (gnn,voice,avatar,remote))}
