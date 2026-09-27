from __future__ import annotations


class GPUResourceManager:
    async def available(self) -> bool:
        return False

    async def can_fit(self, required_vram_mb: int) -> bool:
        return await self.available()

    async def acquire(self, required_vram_mb: int):
        return True

    async def release(self):
        return None

    async def unload_model(self, model_id: str):
        return None
