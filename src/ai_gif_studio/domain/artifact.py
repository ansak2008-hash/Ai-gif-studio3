from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4
@dataclass(frozen=True, slots=True)
class Artifact:
    job_id:UUID
    type:str
    storage_path:str
    mime_type:str
    size_bytes:int
    sha256:str
    artifact_id:UUID=field(default_factory=uuid4)
    created_at:datetime=field(default_factory=lambda:datetime.now(timezone.utc))
    expires_at:datetime|None=None
    metadata:dict[str,object]=field(default_factory=dict)
