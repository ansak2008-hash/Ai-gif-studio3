from __future__ import annotations
from arq import create_pool
from arq.connections import RedisSettings
class ArqQueue:
    def __init__(self,redis_url:str): self.redis_url=redis_url
 self.pool=None
    async def connect(self):
        self.pool=await create_pool(RedisSettings.from_dsn(self.redis_url))
 return self
    async def enqueue_job(self,job_id:str,**kwargs):
        if self.pool is None:
            await self.connect()
        return await self.pool.enqueue_job("process_job",job_id,**kwargs)
    async def close(self):
        if self.pool:
            await self.pool.close()