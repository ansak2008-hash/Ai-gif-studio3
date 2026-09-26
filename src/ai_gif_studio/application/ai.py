from __future__ import annotations
from typing import Protocol,Any
class AIProvider(Protocol):
    async def run(self, workflow:str, inputs:dict[str,Any])->dict[str,Any]: ...
