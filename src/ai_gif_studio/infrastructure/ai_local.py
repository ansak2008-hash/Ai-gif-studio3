from __future__ import annotations
class LocalAIProvider:
    def __init__(self,registry,gpu): self.registry=registry; self.gpu=gpu
    async def run(self,workflow,inputs):
        if workflow!="background_remove": raise ValueError(f"unsupported local workflow: {workflow}")
        raise RuntimeError("No verified local background-removal model is activated; install an approved model and register its exact weights before production use.")
