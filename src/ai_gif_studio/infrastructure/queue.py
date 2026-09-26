from __future__ import annotations
from typing import Protocol
class Queue(Protocol):
    async def enqueue(self,job_id:str)->str: ...
try:
    from arq import create_pool
except ImportError:
    create_pool=None
