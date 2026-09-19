from __future__ import annotations
from collections import defaultdict
import math

class GraphIntelligence:
    """Dependency-aware message-passing scorer.
    Works without ML dependencies now; exposes training examples for a future
    PyTorch-Geometric relational GNN. It never authorizes actions."""
    def __init__(self,graph,memory=None):
        self.graph=graph;self.memory=memory

    @staticmethod
    def _seed_score(node,seeds):
        name=node.get("name","").lower()
        kind=node.get("kind","").lower()
        text=" ".join(str(x).lower() for x in seeds)
        score=0.0
        for token in set(text.replace("/"," ").replace("\\"," ").replace(":"," ").split()):
            if len(token)>2 and token in name: score+=1.0
        if kind in {"file","component","service","endpoint"}:score+=0.1
        return min(score,3.0)

    def rank(self,seeds,hops=3,decay=.65,limit=20):
        snap=self.graph.snapshot(); nodes={n["name"]:n for n in snap["nodes"]}
        adj=defaultdict(list)
        for e in snap["edges"]:
            adj[e["source"]].append((e["target"],e["relation"]))
            adj[e["target"]].append((e["source"],"reverse:"+e["relation"]))
        scores={n:self._seed_score(v,seeds) for n,v in nodes.items()}
        evidence={n:[] for n in nodes}
        for _ in range(max(1,min(int(hops),6))):
            nxt=dict(scores)
            for src,score in scores.items():
                if score<=0:continue
                degree=max(1,len(adj[src]))
                for dst,rel in adj[src]:
                    value=score*float(decay)/math.sqrt(degree*max(1,len(adj[dst])))
                    if value>nxt.get(dst,0):
                        nxt[dst]=value;evidence[dst]=[{"from":src,"relation":rel,"score":round(value,5)}]
            scores=nxt
        ranked=sorted(({"node":n,"kind":nodes[n].get("kind"),"score":round(s,5),"evidence":evidence[n]} for n,s in scores.items() if s>0),key=lambda x:(-x["score"],x["node"]))[:limit]
        return {"mode":"deterministic_message_passing","seeds":list(seeds),"ranked":ranked,"authoritative":False}

    def training_example(self,label,seeds):
        return {"graph":self.graph.snapshot(),"seeds":list(seeds),"label":label}
