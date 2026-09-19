from __future__ import annotations
class OptionalGNNBackend:
    """Optional local PyTorch-Geometric backend. Import is lazy so KRISHNA stays usable without torch."""
    def available(self):
        try:
            import torch
            import torch_geometric
            return True
        except Exception:return False
    def info(self):
        if not self.available():return {"available":False,"backend":"torch_geometric","fallback":"deterministic_message_passing"}
        import torch,torch_geometric
        return {"available":True,"backend":"torch_geometric","torch":torch.__version__,"pyg":torch_geometric.__version__}
