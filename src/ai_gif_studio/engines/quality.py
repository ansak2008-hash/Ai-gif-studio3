from __future__ import annotations
from pathlib import Path
class QualityEngine:
    def validate_size(self,path:Path,max_bytes:int)->bool: return path.exists() and path.stat().st_size<=max_bytes
    def ladder(self,preferred:int)->tuple[int,...]: return tuple(dict.fromkeys((preferred,16,12,10,8,6)))
