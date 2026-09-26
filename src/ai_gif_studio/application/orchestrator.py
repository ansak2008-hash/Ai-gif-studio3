from __future__ import annotations
from pathlib import Path
from uuid import UUID
from ai_gif_studio.domain.specs import ProcessingSettings
from ai_gif_studio.engines.crop import CropOnlyEngine
class JobOrchestrator:
    def __init__(self,crop_engine:CropOnlyEngine): self.crop_engine=crop_engine
    async def run_crop_only(self,job_id:UUID,source:Path,target:Path,settings:ProcessingSettings):
        return await self.crop_engine.convert(source,target,settings)
