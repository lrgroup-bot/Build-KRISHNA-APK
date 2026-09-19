from __future__ import annotations
class LocalGNNTrainer:
 """Local-only trainer boundary. Never fabricates a trained model."""
 def __init__(self,backend,dataset):self.backend=backend;self.dataset=dataset
 def readiness(self,min_examples=50):
  examples=self.dataset.load()
  return {"backend_available":self.backend.available(),"verified_examples":len(examples),"minimum_examples":min_examples,"ready":self.backend.available() and len(examples)>=min_examples}
 def train(self,min_examples=50):
  state=self.readiness(min_examples)
  if not state["ready"]:raise RuntimeError("GNN training prerequisites not satisfied")
  raise NotImplementedError("model architecture/hyperparameters require validated dataset schema before training")
